# LED Lead Outreach Rules

## Target Fit Gate

Only collect and contact companies that are clearly related to LED display, LED screen, LED wall, video wall, digital signage LED, or LED display rental/sales/integration.

A company is a valid target only when at least one of these is clear from its website, social profile, or business listing:

- LED display / LED screen / LED wall / video wall is a core service or product.
- The company rents, sells, installs, integrates, or maintains LED display systems.
- The company is an AV/event production company with an obvious LED wall or LED screen rental/service line.
- The company is a digital signage/sign company with LED display sales or installation.
- For USA batches, the company must also be clearly based in the United States or have a verified US branch/contact page.

Do not contact these unless LED display work is clearly confirmed:

- General party rental companies.
- DJ, lighting-only, decor, photo booth, inflatable, game, or entertainment rental companies.
- Generic AV companies with no visible LED display / LED wall service.
- Mobile advertising companies unless they clearly operate LED screen trucks or LED walls.
- Any account where Instagram/Facebook search selects a non-matching or unrelated profile.
- Any company/profile showing a China, Shenzhen, Guangdong, Hong Kong, or other non-US address when the current task is USA customer development.
- China-based LED manufacturers/suppliers, even if they use English, have US-facing pages, or show LED wall products.

If the target fit is uncertain, keep it as `candidate_unverified` and do not send email, IG, FB, or WA until verified.

Before outreach, check the target's website footer/contact page and IG/FB bio location. If either shows a non-US address for a USA batch, mark `excluded_non_usa_company` and do not send.

## Channel Rules

- Email may use the formal company signature and must include the Korea project case image when available.
- Instagram, Facebook, and WhatsApp must use casual DM format, not email format.
- Instagram, Facebook, and WhatsApp may briefly introduce the sender as: "I'm Allen, from an LED display manufacturing factory in Shenzhen, China." Do not add a long email-style signature block.
- Email may also use a short opening such as "I'm Allen, from an LED display manufacturing factory in Shenzhen, China" before the formal signature.
- Send the Korea project case image with IG/FB/WA whenever the platform automation supports it.
- For Instagram DM image upload, use the DM media input selector `input[type="file"][multiple]`. Do not use plain `input[type="file"]`, because it can select the post-creation input and fail to send the image in DM.
- IG/FB/WA outreach is complete only when the text DM and the case image are both sent or the pipeline explicitly records the image failure reason.
- When sending WhatsApp to a customer, also set the WhatsApp contact note/name to this format: `1_国家_公司名_名字` for fixed-installation/sales/integration customers and `2_国家_公司名_名字` for LED display rental/event/mobile LED truck customers. If the contact person's name is unknown, omit the final name segment. Use Chinese country names in the note, for example `1_美国_公司名_名字`, `2_墨西哥_公司名`, `2_哥伦比亚_公司名`.
- No warmup. Once a verified target is found, contact directly.
