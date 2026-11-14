"""Two-tier place gazetteer for the Pantip Japan graph.

CITIES  : tier 1 nodes (city / region).  id -> (region_group, [aliases])
LANDMARKS: tier 2 nodes.  id -> (parent city id, type, [aliases])

Aliases are lower-case. ASCII aliases match on word boundaries; Thai aliases match as substrings.
Types: city-area, temple/shrine, castle, nature, onsen, theme-park, food/market, shopping, transport-hub, museum/other
"""
import re

CITIES = {
    "Tokyo": ("Kanto", ["โตเกียว", "tokyo", "ชินจูกุ", "shinjuku", "ชิบูย่า", "shibuya", "อาซากุสะ", "asakusa", "อากิฮาบาระ", "akihabara", "อุเอโนะ", "ueno", "ginza", "กินซ่า"]),
    "Osaka": ("Kansai", ["โอซาก้า", "โอซาก้า", "โอซากะ", "osaka"]),
    "Kyoto": ("Kansai", ["เกียวโต", "kyoto"]),
    "Nara": ("Kansai", ["นารา", "nara"]),
    "Kobe": ("Kansai", ["โกเบ", "kobe"]),
    "Himeji": ("Kansai", ["ฮิเมจิ", "himeji"]),
    "Hokkaido": ("Hokkaido", ["ฮอกไกโด", "hokkaido"]),
    "Sapporo": ("Hokkaido", ["ซัปโปโร", "ซัปโปะโระ", "sapporo"]),
    "Otaru": ("Hokkaido", ["โอตารุ", "otaru"]),
    "Hakodate": ("Hokkaido", ["ฮาโกดาเตะ", "hakodate"]),
    "Biei/Furano": ("Hokkaido", ["บิเอ", "biei", "ฟุราโน่", "ฟูราโนะ", "furano"]),
    "Asahikawa": ("Hokkaido", ["อาซาฮิกาวะ", "asahikawa"]),
    "Noboribetsu/Toya": ("Hokkaido", ["โนโบริเบ็ตสึ", "noboribetsu", "โทยะ", "toya"]),
    "Niseko": ("Hokkaido", ["นิเซโกะ", "niseko"]),
    "Fukuoka": ("Kyushu", ["ฟุกุโอกะ", "fukuoka", "hakata", "ฮากาตะ"]),
    "Beppu/Yufuin": ("Kyushu", ["เบปปุ", "beppu", "ยูฟุอิน", "yufuin", "oita", "โออิตะ"]),
    "Kumamoto": ("Kyushu", ["คุมาโมโตะ", "kumamoto"]),
    "Kagoshima": ("Kyushu", ["คาโกชิม่า", "kagoshima"]),
    "Kyushu": ("Kyushu", ["คิวชู", "kyushu"]),
    "Okinawa": ("Okinawa", ["โอกินาว่า", "โอกินาวา", "okinawa"]),
    "Nagoya": ("Chubu", ["นาโกย่า", "nagoya"]),
    "Takayama": ("Chubu", ["ทาคายาม่า", "takayama"]),
    "Shirakawa-go": ("Chubu", ["ชิราคาวาโกะ", "shirakawa"]),
    "Kanazawa": ("Chubu", ["คานาซาว่า", "kanazawa"]),
    "Matsumoto": ("Chubu", ["มัตสึโมโตะ", "matsumoto"]),
    "Fuji/Kawaguchiko": ("Kanto", ["ฟูจิ", "fuji", "คาวากุจิโกะ", "kawaguchiko"]),
    "Hakone": ("Kanto", ["ฮาโกเน่", "ฮาโกเนะ", "hakone"]),
    "Kamakura": ("Kanto", ["คามาคุระ", "kamakura"]),
    "Yokohama": ("Kanto", ["โยโกฮาม่า", "yokohama"]),
    "Nikko": ("Kanto", ["นิกโก้", "นิกโกะ", "nikko"]),
    "Hiroshima": ("Chugoku", ["ฮิโรชิม่า", "ฮิโรชิมะ", "hiroshima", "มิยาจิม่า", "miyajima"]),
    "Tohoku/Sendai": ("Tohoku", ["โทโฮคุ", "tohoku", "เซนได", "sendai"]),
}

LANDMARKS = {
    # Tokyo
    "Shibuya Crossing": ("Tokyo", "city-area", ["shibuya crossing", "ชิบูย่า", "shibuya", "สครัมเบิล"]),
    "Shinjuku": ("Tokyo", "city-area", ["ชินจูกุ", "shinjuku"]),
    "Asakusa / Sensoji": ("Tokyo", "temple/shrine", ["อาซากุสะ", "asakusa", "เซ็นโซจิ", "sensoji", "senso-ji"]),
    "Akihabara": ("Tokyo", "shopping", ["อากิฮาบาระ", "akihabara"]),
    "Ueno": ("Tokyo", "city-area", ["อุเอโนะ", "ueno"]),
    "Ginza": ("Tokyo", "shopping", ["กินซ่า", "ginza"]),
    "Meiji Shrine": ("Tokyo", "temple/shrine", ["ศาลเจ้าเมจิ", "meiji", "เมจิจิงกู"]),
    "Tsukiji": ("Tokyo", "food/market", ["สึคิจิ", "tsukiji"]),
    "Tokyo Disney": ("Tokyo", "theme-park", ["tokyo disney", "disneysea", "ดิสนีย์ซี", "โตเกียวดิสนีย์", "tdl", "tds"]),
    "Tokyo Skytree/Tower": ("Tokyo", "museum/other", ["skytree", "สกายทรี", "tokyo tower", "โตเกียวทาวเวอร์"]),
    "Haneda/Narita": ("Tokyo", "transport-hub", ["haneda", "ฮาเนดะ", "narita", "นาริตะ"]),
    # Osaka
    "Dotonbori": ("Osaka", "food/market", ["dotonbori", "โดทงโบริ", "dotombori"]),
    "Namba": ("Osaka", "city-area", ["namba", "นัมบะ", "nanba"]),
    "Umeda": ("Osaka", "city-area", ["umeda", "อุเมดะ"]),
    "Shinsaibashi": ("Osaka", "shopping", ["shinsaibashi", "ชินไซบาชิ"]),
    "Osaka Castle": ("Osaka", "castle", ["ปราสาทโอซาก้า", "ปราสาทโอซากา", "osaka castle", "osakajo"]),
    "USJ": ("Osaka", "theme-park", ["usj", "universal studios", "ยูนิเวอร์แซล", "ยูเอสเจ", "nintendo world", "นินเทนโด เวิลด์"]),
    "Tennoji": ("Osaka", "city-area", ["tennoji", "เท็นโนจิ", "abeno", "อาเบโนะ", "harukas"]),
    "Kansai Airport": ("Osaka", "transport-hub", ["kansai airport", "kix", "คันไซ แอร์พอร์ต", "haruka", "ฮารุกะ", "nankai", "นันไค"]),
    "Expo 2025": ("Osaka", "museum/other", ["expo", "เอ็กซ์โป", "expo2025"]),
    # Kyoto
    "Fushimi Inari": ("Kyoto", "temple/shrine", ["fushimi inari", "ฟูชิมิ อินาริ", "ฟูชิมิอินาริ", "ฟูชิมิ", "fushimi", "อินาริ"]),
    "Arashiyama": ("Kyoto", "nature", ["arashiyama", "อาราชิยาม่า", "อาราชิยามะ"]),
    "Kiyomizu-dera": ("Kyoto", "temple/shrine", ["kiyomizu", "คิโยมิสึ", "วัดน้ำใส"]),
    "Kinkakuji": ("Kyoto", "temple/shrine", ["kinkaku", "คินคะคุจิ", "วัดทอง"]),
    "Gion": ("Kyoto", "city-area", ["gion", "กิออน"]),
    "Nishiki Market": ("Kyoto", "food/market", ["nishiki", "นิชิกิ"]),
    "Nijo Castle": ("Kyoto", "castle", ["nijo", "นิโจ"]),
    "Kyoto Station": ("Kyoto", "transport-hub", ["kyoto station", "สถานีเกียวโต"]),
    # Nara / Kobe / Himeji
    "Nara Park / Todaiji": ("Nara", "temple/shrine", ["โทไดจิ", "todaiji", "nara park", "สวนนารา", "กวางนารา"]),
    "Himeji Castle": ("Himeji", "castle", ["ปราสาทฮิเมจิ", "himeji castle", "himeji"]),
    "Kobe Beef / Harborland": ("Kobe", "food/market", ["เนื้อโกเบ", "kobe beef", "harborland", "arima", "อาริมะ"]),
    # Hokkaido
    "Susukino": ("Sapporo", "city-area", ["susukino", "ซูซูกิโนะ", "ซูสุกิโนะ"]),
    "Odori Park": ("Sapporo", "nature", ["odori", "โอโดริ"]),
    "Sapporo Clock Tower / TV Tower": ("Sapporo", "museum/other", ["clock tower", "tv tower", "หอนาฬิกา"]),
    "Nijo Market": ("Sapporo", "food/market", ["nijo market", "ตลาดนิโจ"]),
    "Chitose Airport": ("Hokkaido", "transport-hub", ["chitose", "ชิโตเสะ", "ชิโตะเสะ", "new chitose"]),
    "Otaru Canal": ("Otaru", "nature", ["otaru canal", "คลองโอตารุ", "sakaimachi", "ซากาอิมาจิ"]),
    "Hakodate Night View": ("Hakodate", "nature", ["ภูเขาฮาโกดาเตะ", "mt. hakodate", "mount hakodate", "hakodate night", "ฮาโกดาเตะ ไนท์", "goryokaku", "โกเรียวคาคุ", "ตลาดเช้าฮาโกดาเตะ", "hakodate morning market"]),
    "Furano Lavender": ("Biei/Furano", "nature", ["lavender", "ลาเวนเดอร์", "farm tomita", "ฟาร์มโทมิตะ"]),
    "Blue Pond": ("Biei/Furano", "nature", ["blue pond", "บลูพอนด์", "aoiike", "อาโออิเกะ"]),
    "Asahiyama Zoo": ("Asahikawa", "nature", ["asahiyama", "อาซาฮิยาม่า"]),
    "Noboribetsu Jigokudani": ("Noboribetsu/Toya", "onsen", ["jigokudani", "จิโกกุดานิ", "noboribetsu onsen"]),
    "Lake Toya": ("Noboribetsu/Toya", "nature", ["ทะเลสาบโทยะ", "lake toya", "toyako"]),
    "Niseko Ski": ("Niseko", "nature", ["niseko", "นิเซโกะ"]),
    # Kyushu
    "Hakata / Canal City": ("Fukuoka", "shopping", ["canal city", "คาแนลซิตี้", "hakata station", "hakata hankyu", "ฮากาตะ"]),
    "Nakasu Yatai": ("Fukuoka", "food/market", ["yatai", "ยาไตะ", "nakasu", "นากาสุ"]),
    "Dazaifu": ("Fukuoka", "temple/shrine", ["dazaifu", "ดาไซฟุ"]),
    "Fukuoka Airport": ("Fukuoka", "transport-hub", ["fukuoka airport", "สนามบินฟุกุโอกะ"]),
    "Beppu Jigoku": ("Beppu/Yufuin", "onsen", ["beppu", "เบปปุ", "jigoku", "จิโกกุ"]),
    "Yufuin": ("Beppu/Yufuin", "onsen", ["yufuin", "ยูฟุอิน", "lake kinrin", "คินริน"]),
    "Kumamoto Castle": ("Kumamoto", "castle", ["ปราสาทคุมาโมโตะ", "kumamoto castle", "kumamon", "คุมะมง"]),
    "Aso": ("Kumamoto", "nature", ["aso", "อาโสะ", "อะโสะ"]),
    "Sakurajima": ("Kagoshima", "nature", ["sakurajima", "ซากุระจิมะ"]),
    # Okinawa
    "Churaumi Aquarium": ("Okinawa", "nature", ["churaumi", "ชูราอุมิ", "พิพิธภัณฑ์สัตว์น้ำ"]),
    "Naha / Kokusai Dori": ("Okinawa", "city-area", ["naha", "นาฮะ", "นาฮา", "kokusai", "โคคุไซ"]),
    # Chubu
    "Shirakawa-go Village": ("Shirakawa-go", "nature", ["shirakawa", "ชิราคาวาโกะ", "gassho", "กัสโช"]),
    "Takayama Old Town": ("Takayama", "city-area", ["takayama", "ทาคายาม่า", "sanmachi", "ซันมาจิ"]),
    "Kamikochi / Alps": ("Matsumoto", "nature", ["kamikochi", "คามิโคจิ", "alpine route", "tateyama", "ทาเทยาม่า", "อัลไพน์"]),
    "Matsumoto Castle": ("Matsumoto", "castle", ["matsumoto castle", "ปราสาทมัตสึโมโตะ", "matsumoto"]),
    "Kenrokuen": ("Kanazawa", "nature", ["kenrokuen", "เค็นโรคุเอ็น"]),
    "Nagoya Castle / Osu": ("Nagoya", "castle", ["nagoya castle", "ปราสาทนาโกย่า", "osu", "โอสึ", "ghibli park", "จิบลิ", "ghibli"]),
    # Kanto
    "Mt. Fuji": ("Fuji/Kawaguchiko", "nature", ["ภูเขาไฟฟูจิ", "mt. fuji", "mount fuji", "ฟูจิซัง", "fujisan", "chureito", "ชูเรโตะ", "kawaguchiko", "คาวากุจิโกะ", "fuji-q", "fujiq", "ฟูจิคิว"]),
    "Owakudani / Hakone Ropeway": ("Hakone", "nature", ["owakudani", "โอวาคุดานิ", "ropeway", "โรปเวย์", "lake ashi", "ทะเลสาบอาชิ", "gora", "โกระ", "hakone"]),
    "Kamakura Daibutsu / Enoshima": ("Kamakura", "temple/shrine", ["daibutsu", "ไดบุทสึ", "enoshima", "เอโนชิมะ", "slam dunk", "สแลมดังก์", "kamakura"]),
    "Yokohama Minato Mirai": ("Yokohama", "city-area", ["minato mirai", "มินาโตะมิไร", "cup noodle", "คัพนู้ดเดิ้ล", "yokohama"]),
    "Nikko Toshogu": ("Nikko", "temple/shrine", ["toshogu", "โทโชกุ", "kegon", "เคงอน", "nikko", "นิกโก้"]),
    "Gala Yuzawa": ("Tohoku/Sendai", "nature", ["gala yuzawa", "กาล่า ยูซาวะ", "กาล่ายูซาวะ", "yuzawa"]),
    # Chugoku
    "Itsukushima / Miyajima": ("Hiroshima", "temple/shrine", ["miyajima", "มิยาจิม่า", "itsukushima", "อิสึคุชิมะ"]),
    "Peace Memorial": ("Hiroshima", "museum/other", ["peace memorial", "a-bomb", "genbaku", "เก็นบากุ"]),
}

# generic cross-cutting nodes people often pair with places (not geographic)
TRANSPORT_THEMES = {
    "JR Pass": ["jr pass", "เจอาร์พาส", "jrpass", "area pass"],
    "Shinkansen": ["ชินคันเซ็น", "shinkansen"],
}


def _compile(aliases):
    ascii_, thai = [], []
    for a in aliases:
        (ascii_ if a.isascii() else thai).append(a.lower())
    pat = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(a) for a in sorted(ascii_, key=len, reverse=True)) + r")(?![a-z0-9])") if ascii_ else None
    return pat, thai


_C = {k: _compile(v[1]) for k, v in CITIES.items()}
_L = {k: _compile(v[2]) for k, v in LANDMARKS.items()}


def _hit(cm, low):
    pat, thai = cm
    return bool(pat and pat.search(low)) or any(t in low for t in thai)


def find_cities(text):
    low = text.lower()
    return {k for k, cm in _C.items() if _hit(cm, low)}


def find_landmarks(text):
    low = text.lower()
    return {k for k, cm in _L.items() if _hit(cm, low)}
