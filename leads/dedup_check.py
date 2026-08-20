import ast, re, os
base = r"C:\Users\Administrator\ai-topic-generator\output\leads"
_v4_src = open(os.path.join(base, "generate_led_leads_v4.py"), encoding="utf-8").read()
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
for vname in ("v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16",
              "v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27",
              "v28","v29","v30","v31","v32","v33","v34","v35","v36","v37","v38",
              "v39","v40","v41","v42","v43","v44","v45"):
    path = os.path.join(base, f"generate_led_leads_{vname}.py")
    if not os.path.exists(path): continue
    src = open(path, encoding="utf-8").read()
    m = re.search(r"^new_entries = (\[.+?^\])", src, re.M | re.S)
    if m: leads.extend(ast.literal_eval(m.group(1)))
print("Total leads:", len(leads))
checks = [
    "seattlevideowall","lightsmiths","meyerproinc","pixthis",
    "nwvideowall","visibledisplay",
    "avforyou","fireupcreative","palmproductions","erg247",
    "avrexpos","midwestaudio",
    "centricevents","readytoxperience","xperienceent",
    "phoenixledscreens","coloradoliveevents","denvervideowall",
    "MeyerPro","AV For You","Fire Up Creative","Palm Productions",
    "ERG247","AVR Expos","Midwest Audio","Centric Events",
    "Xperience Entertainment","Phoenix LED Screens","Colorado Live","Denver Video Wall",
    "Visible Display","NW Video Wall","Seattle Video Wall","Picture This"
]
for kw in checks:
    found = [l for l in leads if any(kw.lower() in str(v).lower() for v in l.values())]
    if found:
        print("  FOUND no=" + str(found[0]["no"]) + " " + kw + ": " + found[0]["company_en"])
    else:
        print("  NEW   " + kw)
