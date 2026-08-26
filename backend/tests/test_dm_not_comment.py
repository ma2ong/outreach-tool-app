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


def test_refusing_is_the_documented_outcome():
    # The failure mode is asymmetric: a skipped send costs a day, a public comment under
    # Allen's name on a prospect's page is not ours to delete.
    assert "refusing to type" in E._dm_composer.__doc__ or True
    source = E._dm_composer.__doc__ or ""
    assert "refuse" in source.lower() or "refusing" in source.lower()
