from pydantic import BaseModel


class OutreachStatus(BaseModel):
    channel: str
    status: str
    touch_count: int = 0
    message_sent_date: str | None = None
    reply_received: bool = False
    exclude_reason: str | None = None


class Note(BaseModel):
    id: int
    created_at: str | None = None
    text: str


class Template(BaseModel):
    id: int
    name: str
    channel: str
    subject: str | None = None
    body: str
    lang: str | None = None


class SequenceStep(BaseModel):
    step_order: int
    day_offset: int = 0
    subject: str | None = None
    body: str
    image: str | None = None
    # docs/86: a step a person changed in the UI. The seeder leaves it alone.
    edited: bool = False


class Sequence(BaseModel):
    id: int
    name: str
    channel: str
    active: bool = True
    steps: list[SequenceStep] = []
    enrolled: int = 0
    # docs/86 R4: which customers automatic routing sends here. None means manual only.
    segment: str | None = None
    korean: bool = False


class DueItem(BaseModel):
    enrollment_id: int
    lead_no: int
    company_en: str
    channel: str
    sequence_id: int
    sequence_name: str
    step_order: int
    subject: str | None = None
    body: str
    image: str | None = None


class Lead(BaseModel):
    no: int
    company_en: str
    company_local: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    contact_name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    linkedin: str | None = None
    business: str | None = None
    target_fit: str | None = None
    brief: str | None = None
    hook: str | None = None
    email_source: str | None = None
    recheck_due: str | None = None
    whatsapp_verified: bool = False
    email_status: str | None = None
    do_not_contact: bool = False
    stage: str = "new"
    tags: str | None = None
    follow_up_date: str | None = None
    next_action: str | None = None
    source_urls: list[str] = []
    # Read-only, computed for the list view (docs/60): who we deal with there, and the
    # type Allen filed them under rather than the one the classifier guessed.
    primary_contact: str | None = None
    primary_title: str | None = None
    customer_types: list[str] = []
    outreach: list[OutreachStatus] = []
    notes: list[Note] = []


class Stats(BaseModel):
    total: int
    by_country: dict[str, int]
    by_channel_status: dict[str, dict[str, int]]
    reach: dict[str, dict[str, int]] = {}
    funnel: dict[str, int] = {}
