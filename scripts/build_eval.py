"""Rebuild data/eval_v0.csv from the ROWS block below.

ROWS holds the hand-written Vietnamese readings (Northern, colloquial "bồi"
style); ARPAbet comes from CMUdict. Every row has been reviewed by a native
speaker: `corrected` means the reading was changed, `approved` means it stood.

    uv run scripts/build_eval.py [out.csv]
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from boi.g2p import phones  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "eval_v0.csv"

# The Vietnamese word for the thing, where one exists. These are translations,
# not readings, so they stay out of alt_forms and out of the eval target.
VI_NATIVE = {
    "speaker": "loa",
    "mouse": "chuột",
    "bus": "xe buýt",
    "cake": "kêu",
    "steak": "bít tết",
    "icecream": "kem",
    "class": "lớp",
}

# word | vi_form | alt_forms (;) | tags (;) | confidence (h/m/l)
ROWS = """
information|in phô mây sừn||tion;stress3|h
schedule|sờ ke đùa|sờ ket dun|cluster;coda_l|h
context|con tếch||coda_ks|h
computer|com piu tơ|com pu tơ|stress2|h
email|i meo||coda_l|h
internet|in tơ nét||coda_stop|h
online|on lai||diphthong|h
offline|óp lai||coda_stop|h
laptop|láp tốp||coda_stop|h
server|sơ vơ||coda_r|h
database|đa ta bây|đa ta bết|coda_s|m
software|sóp goe||coda_stop|h
hardware|hát goe||coda_stop|m
website|goép sai||coda_stop|h
meeting|mít tinh||ing|h
deadline|đết lai||coda_stop|h
project|pờ rô dếch|prô dếch|cluster;coda_kt;stress1|m
report|rì pọt||stress2;coda_stop|h
file|phai||coda_l|h
folder|phâu đờ||coda_l|m
download|đao lốt||coda_d|h
upload|ắp lốt||coda_d|h
update|ắp đết||coda_stop|h
password|pát guốt||coda_d|h
account|ắc cao||coda_nt;stress2|h
login|lóoc in||coda_stop|h
app|áp||coda_stop|h
code|cốt||coda_d|h
bug|bắc||coda_g|h
test|tét||coda_st|h
data|đa ta|đây ta|open|h
model|mo đồ|mô đen|coda_l|h
training|trên ninh|tờ ren ninh|cluster;ing|m
feedback|phít bách|phít bắc|coda_stop|h
team|tim||coda_m|h
manager|ma na giờ||stress1;coda_r|h
boss|bốt||coda_s|h
company|com pa ni||stress1|h
office|óp phít||coda_s|h
marketing|ma két tinh||ing|h
sale|sêu||coda_l|h
budget|bắt giét||coda_t|m
plan|pờ lan|plan|cluster|h
target|ta ghét||coda_t|m
slide|sờ lai||cluster;coda_d|h
template|tem pờ lết|tem pơ lết;tem lết|cluster;coda_t|h
design|đì dai||stress2;coda_n|h
layout|lây ao||coda_t|h
video|vi đi ô||open|h
camera|ca mê ra||open|h
microphone|mai cờ rô phôn|mic|cluster|m
speaker|sờ pích cơ||cluster;coda_r|h
keyboard|ki bót||coda_d|h
mouse|mao||coda_s|m
screen|sờ cờ rin||cluster3|m
phone|phôn||open|h
smartphone|sờ mát phôn||cluster;coda_t|h
wifi|goai phai|quai phai|open|h
bluetooth|bờ lu tút||cluster;coda_th|h
chat|chát||coda_t|h
message|mét sịt|mét xịt|coda_dj|h
post|pốt||coda_st|h
like|lai||coda_k_drop|h
share|se||coda_r|h
comment|com men||coda_nt|h
follow|pho lâu||open|h
livestream|lai sờ trim||cluster3|h
game|gêm||coda_m|h
level|le vồ|le ven|coda_l|h
player|pờ lây ờ||cluster|m
click|cờ líc|cờ lích|cluster;coda_k|h
link|linh||coda_nk|h
version|vơ dừn||tion|h
system|xít từm|xít tầm;sít tem|coda_m;coda_s|h
network|nét guốc||coda_k|h
cloud|cờ lao||cluster;coda_d|h
machine|mơ sin||stress2|h
learning|lơn ninh||ing|m
algorithm|ao go ri dừm|an gô rít|coda_m;stress1|m
python|pai thừn|pai thon|coda_n|m
java|gia va||open|h
function|phăng sừn||tion|h
option|óp sừn||tion|h
action|ách sừn||tion|h
station|sờ tây sừn||cluster;tion|m
education|e đu cây sừn||tion;stress3|m
presentation|pờ ri den tây sừn|pre zen tây sừn|cluster;tion|m
question|quét sừn|quét chừn|tion|h
solution|sô lu sừn||tion|h
position|pô di sừn||tion|h
fashion|phát sừn||tion|h
shopping|sóp pinh||ing|h
parking|pác kinh||ing|h
singer|sinh gờ||coda_r|m
fan|phan||open|h
idol|ai đồ|ai đôn|coda_l|h
show|sâu||open|h
concert|con sớt||coda_t|h
ticket|tích két|tích kết|coda_t|m
party|pát ti|pác ti|open|h
style|sờ tai||cluster;coda_l|h
size|sai||coda_z|h
shop|xóp||coda_p|h
mall|mô||coda_l|h
hotel|hô theo||stress2;coda_l|h
taxi|tắc xi||coda_ks|h
bus|bớt||coda_s|m
pizza|pi da||open|h
cake|kếch||coda_k|m
burger|bơ gơ||coda_r|h
sandwich|sen guých|xăng uých|coda_ch|m
cheese|chi||coda_z|m
salad|sa lát||coda_d|h
steak|sờ tếch||cluster;coda_k|m
menu|me nu||open|h
juice|giút||coda_s|m
icecream|ai sờ cờ rim||cluster|m
snack|sờ nách||cluster;coda_k|h
sauce|xót||coda_s|h
donut|đô nất||coda_t|h
hello|hê lô|a lô|stress2|h
okay|ô cây||open|h
sorry|so ri||open|h
bye|bai||open|h
baby|bây bi||open|h
happy|háp pi||coda_p|h
family|pham mi li|pham mơ li|stress1|m
friend|phren|phờ ren|cluster;coda_nd|m
love|lớp|lốp|coda_v|h
crush|cờ rắt|cờ rát|cluster;coda_sh|h
date|đết||coda_t|h
cool|cu||coda_l|h
nice|nai||coda_s|h
good|gút||coda_d|h
bad|bét||coda_d|h
very|ve ri||open|h
super|súp pơ||coda_r|h
free|phờ ri|phri|cluster|h
street|sờ trít||cluster3;coda_t|h
spring|sờ pờ rinh|sờ prinh|cluster3;ing|l
strong|sờ trong||cluster3;coda_ng|h
script|sờ críp|sờ cờ ríp|cluster3;coda_pt|m
spray|sờ prây|sờ pờ rây|cluster3|l
school|sờ cun|sờ cu|cluster;coda_l|m
sport|sờ pọt||cluster;coda_rt|h
star|sờ ta||cluster;coda_r|h
stress|sờ trét|xì trét|cluster3;coda_s|h
skill|sờ kiu|sờ kin|cluster;coda_l|h
smile|sờ mai||cluster;coda_l|h
snow|sờ nâu||cluster|m
please|pờ li||cluster;coda_z|h
play|pờ lây||cluster|h
black|bờ lách||cluster;coda_k|h
brown|bờ rao||cluster;coda_n|h
green|gờ rin||cluster;coda_n|h
blue|bờ lu||cluster|h
gray|gờ rây||cluster|h
white|goai|oai|coda_t|m
pink|pinh||coda_nk|h
red|rét|rẹt|coda_d|m
glass|gờ lát||cluster;coda_s|h
clean|cờ lin||cluster;coda_n|h
class|cờ lát||cluster;coda_s|h
group|gờ rúp||cluster;coda_p|h
drama|đờ ra ma||cluster|h
trend|tren|tờ ren|cluster;coda_nd|m
travel|tra vồ|tờ ra ven|cluster;coda_l|l
credit|cờ re đít||cluster;coda_t|m
control|con trôn|con tờ rôn|cluster3;stress2;coda_l|m
event|i ven||stress2;coda_nt|h
image|i mịt|im mịt|coda_dj|m
think|thinh||coda_nk|h
box|bóc||coda_ks|h
banana|ba na na||stress2|h
google|gu gồ||coda_l|h
facebook|phây búc||coda_k|h
youtube|diu túp||coda_b|h
iphone|ai phôn||open|h
netflix|nét phờ lích||cluster;coda_ks|h
microsoft|mai cờ rô sóp||cluster;coda_ft|m
tiktok|tíc tóc||coda_k|h
""".strip()

CORRECTED = set("""
action algorithm baby budget concert control crush database deadline design donut education family fashion folder follow hardware hotel icecream keyboard learning login machine mall manager office okay party player position presentation python report sale sauce shop shopping show singer software speaker super ticket training trend version website white wifi
""".split())



def build(out_path):
    rows = []
    for i, line in enumerate(ROWS.splitlines(), 1):
        word, vi, alt, tags, conf = line.split("|")
        p = phones(word)
        rows.append({
            "id": f"{i:03d}",
            "word": word,
            "arpabet": " ".join(p) if p else "",
            "vi_form": vi,
            "alt_forms": alt,
            "vi_native": VI_NATIVE.get(word, ""),
            "tags": tags,
            "confidence": conf,
            "status": "corrected" if word in CORRECTED else "approved",
        })
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    rows = build(out)
    missing = [r["word"] for r in rows if not r["arpabet"]]
    print(f"{len(rows)} rows -> {out}; missing arpabet: {missing}")
