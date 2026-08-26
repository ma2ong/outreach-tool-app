"""Who this system says it is when it talks to a customer.

One place, because the answer used to live in four code files and twelve rows of copy:
the sender address was hard-coded in the email adapter, the sign-off was baked into the
seeded templates, the quote header carried a different brand again, and the Korean
sequence pasted a personal Gmail into every message. Changing the address meant finding
all sixteen and getting each one right.

The distinction that matters here: **maxcolorvisual.com is the company Allen sells as.**
`mcvisualled.com` is where this tool happens to be hosted, and it must never appear in
anything a customer reads — a supplier who cannot keep its own name straight is not one
you place a purchase order with.

Internal surfaces (the CRM's own title bar, log lines) are free to say whatever is
useful; this module is only about what leaves the building.
"""
from __future__ import annotations

COMPANY = "Shenzhen Maxcolor Visual Co., Ltd."
SENDER_NAME = "Allen Ma"
SENDER_EMAIL = "allen@maxcolorvisual.com"
WHATSAPP = "+86 135-7087-1001"
KAKAO = "+86 13570871001"

# The brand as it appears on a document a customer opens (the quotation header).
BRAND = "MAXCOLOR"

SIGNOFF = f"""Best regards,
{SENDER_NAME}
{COMPANY}
WhatsApp/WeChat: {WHATSAPP}
Email: {SENDER_EMAIL}"""

# Korean buyers do not use WhatsApp, and a Korean cold email does not open with a
# formal self-introduction — so this is not a translation of the English one.
KO_SIGNOFF = f"""{SENDER_NAME}
{COMPANY}
Kakaotalk / WeChat: {KAKAO}
Email: {SENDER_EMAIL}"""

# One line for a quotation footer / PDF contact row.
CONTACT_LINE = f"{SENDER_NAME} · WhatsApp/WeChat {WHATSAPP} · {SENDER_EMAIL}"
