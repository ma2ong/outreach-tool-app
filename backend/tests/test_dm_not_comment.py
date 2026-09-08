"""Never type a cold pitch into a public comment box (docs/61).

Allen's opener appeared under his real name as a public comment on two prospects'
Facebook pages. The chat dock was open at the same time — one screenshot shows the photo
arriving in the DM while the text sat in the comment thread — because the composer was
picked with `.first`, and a page's comment box comes before the chat dock in the DOM.

The fix is an order-of-operations rule, not a better selector: confirm the box is private
before typing, and refuse to send when that cannot be confirmed. These tests hold the
predicate that decides it.
"""
import pytest

from app.playwright_engine import PlaywrightEngine as E


@pytest.mark.parametrize("label", [
    "Write a comment...",
    "以 Allen Ma 的身份评论",
    "写评论",
    "Reply to Jaws Audio",
    "댓글 달기",
    "Comment as Allen Ma",
])
def test_a_comment_box_is_recognised_as_one(label):
    assert E._is_comment_box(label) is True
    assert E._is_dm_box(label) is False


@pytest.mark.parametrize("label", [
    "Message",
    "发消息",
    "发送消息",
    "메시지",
    "Message Jaws Audio",
])
def test_a_message_composer_is_recognised(label):
    assert E._is_dm_box(label) is True


def test_a_box_that_says_both_is_treated_as_a_comment():
    # "Reply to this message" on a public thread is still public. When the two words
    # collide, the safe reading wins.
    assert E._is_dm_box("Reply to message") is False


@pytest.mark.parametrize("label", ["", "Aa", "Search", None])
def test_an_unlabelled_box_is_not_assumed_to_be_private(label):
    # "Aa" is Facebook's own chat placeholder, and it proves nothing on its own: the box
    # has to be found inside a chat surface instead. Guessing here is what caused this.
    assert E._is_dm_box(label or "") is False


# --- probed against a live Facebook page ---

def test_the_real_facebook_comment_box_is_recognised():
    # Exactly what the probe read off the page.
    assert E._is_dm_box("以 Allen Ma 的身份评论") is False


def test_the_real_facebook_dm_composer_is_recognised():
    assert E._is_dm_box("发消息给Jaws Audio") is True


def test_a_composer_aimed_at_another_company_is_rejected():
    # The probe found two docks open at once: Jaws Audio and PRI Productions. "The last
    # message box" would have written this customer's pitch to a different company.
    assert E._addresses("发消息给Jaws Audio", "jawsaudio") is True
    assert E._addresses("发消息给PRI Productions", "jawsaudio") is False


@pytest.mark.parametrize("label,target", [
    ("发消息给Rocky Mountain Roll", "rockymountainroll"),
    ("Message Jaws Audio", "JawsAudio"),
    ("发消息给LED 10", "led10"),
])
def test_name_matching_ignores_spacing_and_case(label, target):
    assert E._addresses(label, target) is True


def test_refusing_is_the_documented_outcome():
    # The failure mode is asymmetric: a skipped send costs a day, a public comment under
    # Allen's name on a prospect's page is not ours to delete.
    assert "refusing to type" in E._dm_composer.__doc__ or True
    source = E._dm_composer.__doc__ or ""
    assert "refuse" in source.lower() or "refusing" in source.lower()


# ---------------------------------------------------------------- docs/99

class _Box:
    """一个页面上的输入框，只带它真实带着的那几个属性。"""

    def __init__(self, **attrs):
        self.attrs = attrs

    def get_attribute(self, name):
        return self.attrs.get(name)

    def is_visible(self):
        return True


class _Page:
    def __init__(self, boxes):
        self._boxes = boxes
        self.waits = 0

    def locator(self, _selector):
        page = self

        class _L:
            def all(self):
                return page._boxes
        return _L()

    def wait_for_timeout(self, _ms):
        self.waits += 1


# 09-04 从真实已登录 profile 上探回来的原文，一个字没改。
IG_DM = _Box(**{"role": "textbox", "contenteditable": "true",
                "aria-placeholder": "发消息...", "data-lexical-editor": "true"})
FB_DM = _Box(**{"aria-label": "发消息给Rentex Audio Visual & Computer Rentals",
                "aria-placeholder": "Aa", "role": "textbox"})
FB_COMMENT = _Box(**{"aria-label": "以 Allen Ma 的身份评论",
                     "aria-placeholder": "以 Allen Ma 的身份评论", "role": "textbox"})


def test_the_instagram_composer_only_labels_itself_in_aria_placeholder():
    """六天沉默的字面原因：读了两个属性，标签在第三个上（docs/99 R1）。"""
    assert E._is_dm_box(E._box_label(IG_DM)) is True


def test_the_facebook_comment_box_labels_itself_there_too():
    """所以补上这个属性同时让评论框更容易被认出，闸门原来对两个方向都是瞎的。"""
    assert E._is_comment_box(E._box_label(FB_COMMENT)) is True


def test_the_only_message_box_on_the_page_is_the_one_we_just_opened():
    """Instagram 的实况：标签里一个字都不提对着谁（docs/99 R2）。"""
    engine = E()
    page = _Page([IG_DM])
    assert engine._dm_composer(page, "digitaloutdooradvertising") is IG_DM


def test_a_handle_that_is_a_contraction_of_the_display_name_still_sends():
    """Facebook 的实况：handle `rentexrentals`，标签里是公司全称，子串比对永远不成立。"""
    engine = E()
    page = _Page([FB_COMMENT, FB_COMMENT, FB_DM])
    assert engine._dm_composer(page, "rentexrentals") is FB_DM


def test_two_docks_neither_naming_the_target_is_still_refused():
    """61 号那条不放宽：两个聊天窗同时开着，猜就是发给陌生公司。"""
    engine = E()
    other = _Box(**{"aria-label": "发消息给PRI Productions"})
    page = _Page([FB_DM, other])
    with pytest.raises(RuntimeError, match="refusing"):
        engine._dm_composer(page, "jawsaudio", timeout=300)


def test_two_docks_where_one_names_the_target_picks_that_one():
    engine = E()
    jaws = _Box(**{"aria-label": "发消息给Jaws Audio"})
    other = _Box(**{"aria-label": "发消息给PRI Productions"})
    page = _Page([other, jaws])
    assert engine._dm_composer(page, "jawsaudio") is jaws


def test_a_page_with_only_comment_boxes_is_refused():
    engine = E()
    page = _Page([FB_COMMENT, FB_COMMENT])
    with pytest.raises(RuntimeError, match="refusing"):
        engine._dm_composer(page, "rentexrentals", timeout=300)


def test_the_refusal_says_what_it_saw():
    """六天里救命的就是这句 `saw:` —— 一个 `(无标签)` 谁也帮不了（docs/99 R4）。"""
    engine = E()
    page = _Page([FB_COMMENT])
    with pytest.raises(RuntimeError) as exc:
        engine._dm_composer(page, "rentexrentals", timeout=300)
    assert "评论" in str(exc.value)


# ---- docs/111：上一家公司的聊天窗还开着 ----

FB_STALE = _Box(**{"aria-label": "发消息给PixelFlex LED", "aria-placeholder": "Aa",
                   "role": "textbox", "data-mc-stale": "1"})


def test_a_leftover_dock_is_never_the_box_we_just_opened():
    """09-08 真实事故：EKM 的信落进了 PixelFLEX 的对话框（docs/111）。

    页面上只有一个聊天框，但它是导航之前就开着的那一个 —— 旧规则「只有一个就是它」
    会把它交出去。
    """
    engine = E()
    page = _Page([FB_STALE])
    with pytest.raises(RuntimeError, match="refusing"):
        engine._dm_composer(page, "EKMexports", timeout=300)


def test_the_refusal_names_the_company_the_leftover_dock_belongs_to():
    engine = E()
    page = _Page([FB_STALE])
    with pytest.raises(RuntimeError) as exc:
        engine._dm_composer(page, "EKMexports", timeout=300)
    assert "PixelFlex LED" in str(exc.value)


def test_the_box_that_opened_now_wins_over_the_one_that_was_open_before():
    engine = E()
    fresh = _Box(**{"aria-label": "发消息给EKM Exports", "role": "textbox"})
    page = _Page([FB_STALE, fresh])
    assert engine._dm_composer(page, "EKMexports") is fresh


def test_an_unlabelled_fresh_box_still_sends():
    """Instagram 的框什么都不写（docs/99 R2）—— 标记机制不能把它一起挡掉。"""
    engine = E()
    page = _Page([FB_STALE, IG_DM])
    assert engine._dm_composer(page, "digitaloutdooradvertising") is IG_DM


def test_the_same_companys_dock_already_open_is_still_usable_when_it_names_them():
    """本来就开着这一家的窗口，点「发消息」不会再开一个 —— 认得出名字就用它。"""
    engine = E()
    page = _Page([FB_STALE])
    assert engine._dm_composer(page, "PixelFlexLED") is FB_STALE


# ---- docs/111 R3：读主页读的是主内容区，不是整页 ----

class _MainPage:
    """主内容区有货、body 里还挂着上一家公司的聊天浮层。"""

    def __init__(self, main_text, body_text):
        self.main_text, self.body_text = main_text, body_text

    def locator(self, _selector):
        page = self

        class _L:
            @property
            def first(self):
                return self

            def is_visible(self, timeout=None):
                return page.main_text is not None

            def inner_text(self):
                return page.main_text
        return _L()

    def inner_text(self, _selector):
        return self.body_text


def test_the_chat_overlay_is_not_this_companys_profile():
    engine = E()
    page = _MainPage("EKM Exports. " + "We export produce. " * 20,
                     "EKM Exports … 发消息给PixelFlex LED: Hi Steve Paladino, saw the rental work")
    assert "PixelFlex" not in engine._profile_text(page)


def test_a_page_without_a_main_falls_back_to_the_whole_body():
    engine = E()
    assert engine._profile_text(_MainPage(None, "whole page")) == "whole page"


def test_an_almost_empty_main_falls_back_too():
    """主内容区还没渲染出来时，读到的两个字不该被当成这家公司的全部内容。"""
    engine = E()
    assert engine._profile_text(_MainPage("加载中", "whole page")) == "whole page"
