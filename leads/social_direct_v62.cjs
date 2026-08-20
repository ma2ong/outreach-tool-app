const fs = require("fs");
const WebSocket = require("ws");

const TODAY = new Date().toISOString().slice(0, 10);
const IMAGE_PATH = "C:\\Users\\Administrator\\Desktop\\Recent-led-projects-poster-4k.jpg";
const BASE = "output/leads/pipeline";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class Page {
  constructor(target) {
    this.id = target.id;
    this.ws = new WebSocket(target.webSocketDebuggerUrl);
    this.seq = 0;
    this.pending = new Map();
  }

  async ready() {
    await new Promise((resolve, reject) => {
      this.ws.once("open", resolve);
      this.ws.once("error", reject);
    });
    this.ws.on("message", (buf) => {
      const msg = JSON.parse(buf.toString());
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        resolve(msg);
      }
    });
  }

  cmd(method, params = {}, timeout = 20000) {
    const id = ++this.seq;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        resolve({ error: { message: "timeout" } });
      }, timeout);
      this.pending.set(id, {
        resolve: (msg) => {
          clearTimeout(timer);
          resolve(msg);
        },
      });
    });
  }

  async eval(expression, timeout = 20000) {
    const resp = await this.cmd("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    }, timeout);
    return resp.result?.result?.value;
  }

  async type(text) {
    return this.cmd("Input.insertText", { text }, 30000);
  }

  async setFiles(selector) {
    await this.cmd("DOM.enable");
    const doc = await this.cmd("DOM.getDocument", {});
    const root = doc.result?.root?.nodeId;
    if (!root) return { success: false, error: "no_document" };
    const node = await this.cmd("DOM.querySelector", { nodeId: root, selector });
    if (!node.result?.nodeId) return { success: false, error: `missing ${selector}` };
    await this.cmd("DOM.setFileInputFiles", { nodeId: node.result.nodeId, files: [IMAGE_PATH] }, 30000);
    return { success: true, files: 1 };
  }

  async close() {
    try { this.ws.close(); } catch {}
    try { await fetch(`http://127.0.0.1:9222/json/close/${this.id}`); } catch {}
  }
}

async function newPage(url) {
  const resp = await fetch(`http://127.0.0.1:9222/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
  if (!resp.ok) throw new Error(`new page failed: ${resp.status}`);
  const target = await resp.json();
  const page = new Page(target);
  await page.ready();
  await sleep(8000);
  return page;
}

function readPipeline(channel) {
  const path = `${BASE}/${channel}/prospects.json`;
  return { path, data: JSON.parse(fs.readFileSync(path, "utf8")) };
}

function savePipeline(path, data) {
  fs.writeFileSync(path, JSON.stringify(data, null, 2), "utf8");
}

function mark(channel, target, fields) {
  const { path, data } = readPipeline(channel);
  const payload = {
    no: target.no,
    country: "USA",
    company_en: target.company_en,
    city: target.city,
    target_fit: "verified_led_display",
    do_not_contact: false,
    ...fields,
  };
  const key = channel === "whatsapp" ? "phone" : channel === "email" ? "email" : "username";
  const value = payload[key] || target[key] || target.facebook || target.instagram;
  const row = data.find((x) => x.no === target.no || (value && String(x[key] || x.username || "").toLowerCase() === String(value).toLowerCase()));
  if (row) Object.assign(row, payload);
  else data.push(payload);
  savePipeline(path, data);
}

async function clickText(page, labels) {
  return page.eval(`
(() => {
  const labels = ${JSON.stringify(labels.map((x) => x.toLowerCase()))};
  const items = Array.from(document.querySelectorAll("a,button,[role=button]"));
  const el = items.find(x => {
    const t = (x.innerText || x.getAttribute("aria-label") || "").trim().toLowerCase();
    return labels.includes(t) || labels.some(l => t.includes(l));
  });
  if (el) { el.click(); return JSON.stringify({ok:true,text:(el.innerText||el.getAttribute("aria-label")||"").trim()}); }
  return JSON.stringify({ok:false});
})()
`);
}

async function clickSend(page) {
  const raw = await page.eval(`
(() => {
  const span = document.querySelector('span[data-icon="wds-ic-send-filled"]') || document.querySelector('span[data-icon="send"]');
  if (span) {
    let el = span;
    for (let i=0;i<8;i++) {
      if (el.tagName === "BUTTON" || el.getAttribute("role") === "button") { el.click(); return JSON.stringify({ok:true, via:"icon"}); }
      if (!el.parentElement) break;
      el = el.parentElement;
    }
    span.click(); return JSON.stringify({ok:true, via:"span"});
  }
  const buttons = Array.from(document.querySelectorAll("button,[role=button]"));
  const b = buttons.find(x => {
    const t=(x.innerText || x.getAttribute("aria-label") || "").trim().toLowerCase();
    return t === "send" || t === "发送" || t.includes("press enter to send");
  });
  if (b) { b.click(); return JSON.stringify({ok:true, via:"text"}); }
  return JSON.stringify({ok:false});
})()
`, 15000);
  try { return JSON.parse(raw || "{}").ok === true; } catch { return false; }
}

async function focusTextbox(page) {
  await page.eval(`
(() => {
  const boxes = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox],textarea"));
  const box = boxes.find(e => e.offsetParent !== null) || boxes[boxes.length - 1];
  if (box) { box.focus(); box.click(); return true; }
  return false;
})()
`);
  await sleep(500);
}

async function inputLen(page) {
  const val = await page.eval(`
(() => {
  const boxes = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox],textarea"));
  const box = boxes.find(e => e.offsetParent !== null) || boxes[boxes.length - 1];
  return box ? String((box.innerText || box.value || "").trim().length) : "0";
})()
`);
  return parseInt(val || "0", 10);
}

async function sendText(page, message) {
  await focusTextbox(page);
  await page.type(message);
  await sleep(1000);
  const len = await inputLen(page);
  console.log("  input len:", len);
  if (len < 10) return false;
  return clickSend(page);
}

async function sendImage(page, selector) {
  const upload = await page.setFiles(selector);
  console.log("  setFiles:", upload);
  if (!upload.success) return false;
  await sleep(5000);
  return clickSend(page);
}

const igTargets = [
  {
    no: 800, username: "funflicksusa", company_en: "FunFlicks Kentucky", city: "Lexington / Louisville, KY",
    message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Kentucky LED screen rental work for outdoor movies, live sports and community events. Sharing a recent Korea LED installation reference. For local events, do clients ask more for trailer LED screens or modular LED walls?",
  },
  {
    no: 801, username: "royalavsolutions", company_en: "Royal AV Solutions", city: "Seattle / Bellevue, WA",
    message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle/Pacific Northwest event AV work and LED video wall rental references. Sharing a recent Korea LED installation reference. For corporate events, do clients request more fine-pitch indoor LED or larger rental walls?",
  },
];

const fbTargets = [
  {
    no: 799, facebook: "ledtrucks", username: "ledtrucks", company_en: "Legion LED Trucks", city: "Bellevue, NE",
    message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Legion LED truck and mobile billboard trailer work. Sharing a recent Korea LED installation reference. For LED trucks, what pixel pitch and cabinet serviceability do your buyers care about most?",
  },
  {
    no: 800, facebook: "funflicks", username: "funflicks", company_en: "FunFlicks Kentucky", city: "Lexington / Louisville, KY",
    message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Kentucky LED screen rental work for outdoor movies and live sports. Sharing a recent Korea LED installation reference. Do clients usually ask for trailer LED screens or modular LED walls?",
  },
  {
    no: 801, facebook: "royalavsolutions", username: "royalavsolutions", company_en: "Royal AV Solutions", city: "Seattle / Bellevue, WA",
    message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle/Pacific Northwest event AV work and LED video wall rental references. Sharing a recent Korea LED installation reference. For corporate events, do clients request more fine-pitch indoor LED or larger rental walls?",
  },
  {
    no: 802, facebook: "GameCrazeParty", username: "GameCrazeParty", company_en: "Game Craze Party Rentals", city: "Northeast Ohio",
    message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Northeast Ohio LED video wall rental page with 14ft x 8ft LED walls. Sharing a recent Korea LED installation reference. Are your LED wall jobs mostly schools/churches or corporate events?",
  },
];

const waTargets = [
  { no: 798, company_en: "LED Screen Rentals", city: "Los Angeles / nationwide", phone: "+1 833 403 0420", message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED screen, LED display and LED wall rental work and wanted to share a recent Korea LED installation reference. Do clients usually ask more for mobile LED screens or modular indoor/outdoor LED walls?" },
  { no: 799, company_en: "Legion LED Trucks", city: "Bellevue, NE", phone: "+1 866 792 9533", message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Legion LED truck and mobile billboard trailer work and wanted to share a recent Korea LED installation reference. For LED trucks, what pixel pitch and cabinet serviceability do your buyers care about most?" },
  { no: 800, company_en: "FunFlicks Kentucky", city: "Lexington / Louisville, KY", phone: "+1 859 869 9669", message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Kentucky LED screen rental work for outdoor movies, live sports and community events. Sharing a recent Korea LED installation reference. Do clients usually ask for trailer LED screens or modular LED walls?" },
  { no: 801, company_en: "Royal AV Solutions", city: "Seattle / Bellevue, WA", phone: "+1 206 580 3040", message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle/Pacific Northwest event AV work and LED video wall rental references. Sharing a recent Korea LED installation reference. For corporate events, do clients request more fine-pitch indoor LED or larger rental walls?" },
  { no: 802, company_en: "Game Craze Party Rentals", city: "Northeast Ohio", phone: "+1 330 752 2351", message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Northeast Ohio LED video wall rental page with 14ft x 8ft LED walls. Sharing a recent Korea LED installation reference. Are your LED wall jobs mostly schools/churches or corporate events?" },
  { no: 803, company_en: "Freedom Fun USA Dayton", city: "Franklin / Dayton, OH", phone: "+1 937 970 4386", message: "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Dayton LED Screen & Video Wall Rentals page with 17ft x 10ft and 23ft x 13ft mobile LED screens. Sharing a recent Korea LED installation reference. Are your events mostly outdoor community screens or corporate brand activations?" },
];

async function sendIg(t) {
  console.log(`\nIG @${t.username} | no:${t.no}`);
  let page;
  try {
    page = await newPage(`https://www.instagram.com/${t.username}/`);
    const url = await page.eval("location.href");
    console.log("  url:", url);
    await clickText(page, ["Follow", "关注"]);
    await sleep(2000);
    const msg = await clickText(page, ["Message", "发消息"]);
    console.log("  message:", msg);
    await sleep(7000);
    const image = await sendImage(page, 'input[type="file"][multiple]');
    await sleep(2500);
    const text = await sendText(page, t.message);
    mark("instagram", t, {
      platform: "instagram", username: t.username, followed: true, image_sent: image,
      attachment: IMAGE_PATH,
      ...(text ? { status: "messaged", touch_count: 1, message_sent_date: TODAY, message_channel: "instagram", message_text: t.message, image_sent_date: image ? TODAY : undefined } : { status: "prospect", last_attempt_date: TODAY, last_attempt_result: image ? "text_not_sent" : "image_and_text_not_sent" }),
    });
    console.log(`  ${text ? "SENT" : "FAILED"} | image=${image}`);
  } catch (e) {
    console.log("  FAILED", e.message);
    mark("instagram", t, { platform: "instagram", username: t.username, status: "prospect", last_attempt_date: TODAY, last_attempt_result: e.message, image_sent: false, attachment: IMAGE_PATH });
  } finally {
    if (page) await page.close();
  }
}

async function sendFb(t) {
  console.log(`\nFB ${t.facebook} | no:${t.no}`);
  let page;
  try {
    page = await newPage(`https://www.facebook.com/${t.facebook}`);
    const url = await page.eval("location.href");
    console.log("  url:", url);
    await clickText(page, ["Follow", "Like", "关注", "赞"]);
    await sleep(2000);
    const msg = await clickText(page, ["Message", "Send message", "发消息", "消息"]);
    console.log("  message:", msg);
    await sleep(7000);
    const image = await sendImage(page, 'input[type="file"]');
    await sleep(2500);
    const text = await sendText(page, t.message);
    mark("facebook", t, {
      platform: "facebook", username: t.facebook, facebook: t.facebook, followed: true, image_sent: image,
      attachment: IMAGE_PATH,
      ...(text ? { status: "messaged", touch_count: 1, message_sent_date: TODAY, message_channel: "facebook", message_text: t.message, image_sent_date: image ? TODAY : undefined, last_attempt_result: null, last_attempt_date: null } : { status: "prospect", last_attempt_date: TODAY, last_attempt_result: image ? "text_not_sent" : "image_and_text_not_sent" }),
    });
    console.log(`  ${text ? "SENT" : "FAILED"} | image=${image}`);
  } catch (e) {
    console.log("  FAILED", e.message);
    mark("facebook", t, { platform: "facebook", username: t.facebook, facebook: t.facebook, status: "prospect", last_attempt_date: TODAY, last_attempt_result: e.message, image_sent: false, attachment: IMAGE_PATH });
  } finally {
    if (page) await page.close();
  }
}

async function sendWa(t) {
  console.log(`\nWA ${t.phone} | no:${t.no}`);
  let page;
  try {
    const phone = t.phone.replace(/\D/g, "");
    const url = `https://web.whatsapp.com/send?phone=${phone}&text=${encodeURIComponent(t.message)}`;
    page = await newPage(url);
    console.log("  url:", await page.eval("location.href"));
    let text = false;
    for (let i = 0; i < 70; i++) {
      text = await clickSend(page);
      if (text) break;
      await sleep(200);
    }
    let image = false;
    if (text) {
      await sleep(2500);
      image = await sendImage(page, 'input[type="file"]');
    }
    mark("whatsapp", t, {
      platform: "whatsapp", username: t.phone, phone: t.phone, whatsapp_verified: false,
      ...(text ? { status: "messaged", touch_count: 1, message_sent_date: TODAY, message_channel: "whatsapp", message_text: t.message, image_sent: image, image_sent_date: image ? TODAY : undefined, attachment: IMAGE_PATH, last_attempt_result: null, last_attempt_date: null } : { status: "prospect", last_attempt_date: TODAY, last_attempt_result: "text_not_sent" }),
    });
    console.log(`  ${text ? "SENT" : "FAILED"} | image=${image}`);
  } catch (e) {
    console.log("  FAILED", e.message);
    mark("whatsapp", t, { platform: "whatsapp", username: t.phone, phone: t.phone, status: "prospect", last_attempt_date: TODAY, last_attempt_result: e.message });
  } finally {
    if (page) await page.close();
  }
}

(async () => {
  console.log(`=== Direct Social/WA v62 | ${TODAY} ===`);
  for (const t of igTargets) await sendIg(t);
  for (const t of fbTargets) await sendFb(t);
  for (const t of waTargets) await sendWa(t);
})();
