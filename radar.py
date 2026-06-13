#!/usr/bin/env python3
"""
Tech Radar v2 — 동적 딥테크 트렌드 발견 + 예측 대시보드

고정 키워드를 쓰지 않는다. arXiv 최근 논문에서 기술용어를 직접 발견하고,
각 용어의 시계열을 모은 뒤, 감쇠 Holt 지수평활로 다음 분기를 예측한다.
백테스트(MAPE)로 예측 정확도를 검증한다.

사용법:
    python3 radar.py harvest   # 최근 논문 수집 → 용어 발견
    python3 radar.py series    # 발견 용어들의 월간 시계열 수집(캐시)
    python3 radar.py analyze   # 지표·예측·백테스트 계산 → data.json
    python3 radar.py build     # dashboard.html 생성
    python3 radar.py all       # 전체
    python3 radar.py smoke     # 소규모 검증
"""
import sys, os, json, time, math, re, urllib.parse, urllib.request
from datetime import date, datetime
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(HERE, "corpus.json")
TERMS_PATH  = os.path.join(HERE, "terms.json")
CACHE_PATH  = os.path.join(HERE, "cache.json")
DATA_PATH   = os.path.join(HERE, "data.json")
HTML_PATH   = os.path.join(HERE, "dashboard.html")

API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
OS_NS = {"o": "http://a9.com/-/spec/opensearch/1.1/"}
DELAY = 5.0

# 딥테크 범위(카테고리만 고정 — 키워드는 동적 발견)
CATEGORIES = [
    "cs.AI","cs.LG","cs.CL","cs.CV","cs.RO","cs.NE",
    "quant-ph","q-bio.BM","q-bio.GN",
    "cond-mat.mtrl-sci","cond-mat.supr-con",
    "physics.app-ph","physics.plasm-ph","eess.SY",
]
MONTHS        = 12     # 시계열 길이
N_TERMS       = 20     # 발견할 용어 수
HARVEST_DAYS  = 75     # 발견용 최근 윈도우(일)
PAGE_SIZE     = 50
MAX_PAGES     = 16     # 최대 수집 논문 = PAGE_SIZE*MAX_PAGES

# ── 불용어 / 학술 상투어 ──────────────────────────────────────────────────
STOP = set("""a an the of for to in on at by and or with without from into over under
as is are was were be been being this that these those we our it its their they them
us you your he she his her not no can may will would could should our can't using use
used uses we present propose proposed approach method methods model models framework
results result show shows shown novel new paper study studies based via toward towards
between among within across through during about more most less than then thus hence
which who whom whose what when where why how all any some each both few many much such
also however therefore moreover furthermore additionally respectively e.g i.e et al
one two three first second third high low large small good better best high-quality
given due according compared comparison performance accuracy efficient effective
state art state-of-the-art datasets dataset data set sets task tasks problem problems
work works system systems analysis based learning learn training train test testing
network networks deep machine algorithm algorithms function functions value values
information number numbers level levels case cases time times step steps process
significant significantly improve improved improvement improvements demonstrate
demonstrated achieve achieved able enable enables enabled provide provides provided
require requires required different various several existing recent recently general
specific particular important key main major potential possible significant
often well may might while since though although whether either neither especially
particularly typically usually generally commonly finally simply directly currently
previously prior post pre non per still yet already always never sometimes rather
quite very too enough only just even much many lot lots make makes made making find
found finding get gets got take takes taken give gives given become becomes remain
remains allow allows allowing lead leads leading help helps need needs want wants
consider considered observe observed obtain obtained obtaining develop developed
developing introduce introduced introducing address addressed addressing focus focused
focusing aim aims aimed exhibit exhibits leverage leverages leveraging utilize utilizes
employ employs employed apply applies applied evaluate evaluated evaluating evaluation
compare compares compared comparing predict predicts predicted estimate estimated
generate generates generated generating learn learns learned define defines defined
include includes including consist consists contain contains containing involve involves
explore explores explored investigate investigated examine examined analyze analyzed
report reports reported observe present presents presented presenting describe described
called termed namely whereas thereby whose toward upward downward overall together
across along around within without beyond hence thus therefore moreover furthermore
additionally consequently accordingly subsequently meanwhile nevertheless nonetheless
respectively similarly likewise instead unlike despite regardless
every shared strongest consistently improves improving stronger weaker larger smaller
higher lower greater fewer better best worse worst good bad early late fast slow easy
hard full empty true false real same equal entire whole partial single double multiple
diverse wide narrow broad shallow dense sparse robust stable powerful strong weak
notable remarkable substantial considerable extensive comprehensive thorough detailed
precise accurate exact approximate rough total initial primary secondary central core
basic fundamental essential crucial critical vital necessary sufficient adequate
appropriate suitable relevant useful helpful valuable promising interesting surprising
clear obvious evident apparent likely unlikely probable certain uncertain frequent
occasional typical standard normal regular special unique original modern following
moreover additionally simple complex efficient effective significant superior optimal
existing proposed but have has had having will shall must let lets able than once upon
onto evidence magnitude percentage points cost modes families success rate rates ratio
gains gap gaps margin margins terms order orders kind kinds way ways amount amounts
findings finding suggest suggests suggested mode insights insight observation observations
implications implication setting settings scenario scenarios setup phenomenon phenomena""".split())

# 너무 일반적/확립된 구 (떠오르는 트렌드 아님) → 제외
GENERIC = set([
    "neural network","neural networks","deep learning","machine learning","large language",
    "language model","language models","large language model","deep neural","deep neural network",
    "convolutional neural","convolutional neural network","training data","data driven",
    "real world","high dimensional","open source","experimental results","extensive experiments",
    "wide range","first time","ablation study","ablation studies","downstream tasks",
    "downstream task","empirical results","state art","prior work","related work","case study",
    "training process","test set","training set","data set","model performance","model parameters",
    "neural networks trained","loss function","objective function","ground truth","data points",
    "model families","task success","computational cost","model family","model size","model sizes",
    "model capabilities","model outputs","model behavior","real time","high quality","large scale",
    "unified framework","general framework","novel framework","new framework","visual features",
    "key challenge","key challenges","open problem","open challenges","broad range",
])

# 연결어: 다중어 구의 '내부'에만 허용 (경계 불가). of/and만 — 나머지는 단편 신호
CONNECTORS = {"of","and"}

# 핵심 기술 명사: 단독이면 범용이나 구의 일부로는 필수 → 불용어 취급 안 함
HEAD = set("""model models network networks learning method methods framework frameworks
system systems data task tasks approach algorithm algorithms function functions analysis
performance training baseline baselines benchmark benchmarks feature features representation
representations architecture architectures policy policies reasoning generation detection
segmentation prediction estimation optimization attention embedding embeddings inference
transformer transformers diffusion gradient sampling alignment tuning prompt prompts token
tokens agent agents reward retrieval planning control perception fusion encoder decoder
distillation pretraining finetuning quantization compression supervision classification
recognition tracking localization reconstruction generative discriminative graph kernel
manifold latent autoregressive multimodal language vision speech audio video image text
robot robotic quantum molecular protein genomic neural spiking photonic memristor qubit""".split())

# ── HTTP ──────────────────────────────────────────────────────────────────
def api_get(params, retries=5):
    url = API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"tech-radar/2.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return ET.fromstring(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:                       # 속도제한 → 길게 백오프
                wait = 30 * (a+1)
                sys.stderr.write(f"  ! 429 속도제한, {wait}s 대기 ({a+1}/{retries})\n")
                time.sleep(wait)
            else:
                sys.stderr.write(f"  ! HTTP {e.code} 재시도 ({a+1}/{retries})\n")
                time.sleep(DELAY*2)
        except Exception as e:
            sys.stderr.write(f"  ! 재시도 {a+1}/{retries}: {e}\n")
            time.sleep(DELAY*2)
    return None

# ── A. 발견용 코퍼스 수집 (전경=최근, 배경=1년 전 동기간) ──────────────────
def _harvest_window(cat_q, end_ago, days, max_pages, tag):
    today = date.today()
    ed_ord = today.toordinal() - end_ago
    sd = date.fromordinal(ed_ord - days).strftime("%Y%m%d") + "0000"
    ed = date.fromordinal(ed_ord).strftime("%Y%m%d") + "2359"
    sq = f"({cat_q}) AND submittedDate:[{sd} TO {ed}]"
    docs=[]
    for page in range(max_pages):
        root = api_get({"search_query": sq, "start": page*PAGE_SIZE,
                        "max_results": PAGE_SIZE})   # 정렬 제거(스로틀 회피)
        if root is None: break
        entries = root.findall(f"{ATOM}entry")
        if not entries: break
        for e in entries:
            t=(e.findtext(f"{ATOM}title") or "").strip()
            s=(e.findtext(f"{ATOM}summary") or "").strip()
            docs.append(t+". "+s)
        print(f"[{tag}] page {page+1}: +{len(entries)} (누적 {len(docs)})")
        time.sleep(DELAY)
    return docs

def harvest(categories=CATEGORIES, days=HARVEST_DAYS, max_pages=MAX_PAGES):
    cat_q = " OR ".join(f"cat:{c}" for c in categories)
    fg = _harvest_window(cat_q, 0,   days, max_pages, "전경")
    bg = _harvest_window(cat_q, 365, days, max_pages, "배경")
    with open(CORPUS_PATH,"w") as f:
        json.dump({"window_days":days,"count":len(fg),"bg_count":len(bg),
                   "fg":fg,"bg":bg}, f, ensure_ascii=False)
    print(f"✓ 코퍼스 저장: 전경 {len(fg)}편 / 배경 {len(bg)}편")
    return {"fg":fg,"bg":bg}

# ── 용어 추출 ──────────────────────────────────────────────────────────────
def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\- ]", " ", text)
    toks = [w for w in text.split() if len(w) > 1]
    return toks

def is_good_token(w):
    return (w not in STOP) and (not w.isdigit()) and len(w) >= 3 and "-" not in w[:1]

def _blocked(g):
    """이 토큰이 용어에 들어갈 수 없으면 True (핵심명사/연결어는 허용)."""
    return (g in STOP) and (g not in HEAD) and (g not in CONNECTORS)

def _doc_freq(docs):
    """다중어(2~3gram) 기술구만 추출. 단일어 폐기."""
    from collections import Counter
    df = Counter()
    for d in docs:
        toks = tokenize(d)
        seen = set()
        for k in (2,3):
            for i in range(len(toks)-k+1):
                gram = toks[i:i+k]
                first, last = gram[0], gram[-1]
                # 경계: 불용어/연결어 불가 (핵심명사는 허용)
                if _blocked(first) or first in CONNECTORS: continue
                if _blocked(last)  or last in CONNECTORS: continue
                if any(_blocked(g) for g in gram[1:-1]): continue   # 내부는 연결어/핵심명사 허용
                if any(g.isdigit() for g in gram): continue
                if len(first) < 3 or len(last) < 3: continue
                term = " ".join(gram)
                if term in GENERIC: continue
                seen.add(term)
        for term in seen: df[term]+=1
    return df

def extract_terms(corpus, n=N_TERMS):
    """전경/배경 비교(lift)로 '지금 유독 떠오르는' 기술용어를 발견."""
    fg_docs = corpus["fg"]; bg_docs = corpus.get("bg",[])
    df_fg = _doc_freq(fg_docs)
    df_bg = _doc_freq(bg_docs) if bg_docs else None
    Nf = max(len(fg_docs),1); Nb = max(len(bg_docs),1)
    min_df = max(8, int(Nf*0.012))

    cand=[]
    for term, cf in df_fg.items():
        if cf < min_df: continue
        nw = term.count(" ")+1
        rate_fg = (cf+0.5)/(Nf+1)
        if df_bg is not None:
            cb = df_bg.get(term,0)
            rate_bg = (cb+0.5)/(Nb+1)
            lift = rate_fg/rate_bg
        else:
            lift = 1.0
        # 상승하지 않는(lift<1.1) 범용어는 제외 → 떠오르는 것만
        if lift < 1.3: continue
        mw = 1.0 + 0.5*(nw-1)            # 멀티워드 가산
        score = (cf**0.7) * min(lift, 5.0) * mw   # df 비중↑로 희귀 노이즈 억제
        cand.append((term, cf, nw, round(lift,2), score))
    cand.sort(key=lambda x:-x[4])

    # 토큰집합 Jaccard 중복 제거 (단/복수·VLA 변형 병합)
    def stem(w): return w[:-1] if w.endswith("s") and len(w)>3 else w
    def jacc(a,b):
        A={stem(w) for w in a.split()}; B={stem(w) for w in b.split()}
        return len(A&B)/len(A|B) if A|B else 0
    chosen=[]
    for term, cf, nw, lift, sc in cand:
        if any(jacc(term,ct)>0.5 for ct,_,_,_ in chosen): continue
        chosen.append((term,cf,nw,lift))
        if len(chosen)>=n: break

    terms=[{"term":t,"df":c,"nwords":nw,"lift":lf} for t,c,nw,lf in chosen]
    json.dump(terms, open(TERMS_PATH,"w"), ensure_ascii=False, indent=2)
    print(f"✓ 용어 {len(terms)}개 발견 (lift 기준 상승 용어)")
    for i,t in enumerate(terms):
        print(f"   {i+1:2d}. {t['term']}  (df={t['df']}, lift={t['lift']}×)")
    return terms

# ── B. 시계열 ──────────────────────────────────────────────────────────────
def month_ranges(n):
    today = date.today(); y,m = today.year, today.month
    out=[]
    for _ in range(n):
        m -= 1
        if m==0: m=12; y-=1
        s=f"{y:04d}{m:02d}010000"
        ny,nm = (y+1,1) if m==12 else (y,m+1)
        e=f"{ny:04d}{nm:02d}010000"
        out.append((f"{y:04d}-{m:02d}", s, e))
    out.reverse(); return out

def load_cache():
    return json.load(open(CACHE_PATH)) if os.path.exists(CACHE_PATH) else {}

def term_query(term):
    """2단어 이하는 정확한 구(정밀), 3단어+는 토큰 AND(약어·어순 견고)."""
    toks = [t for t in term.split() if t not in CONNECTORS and len(t) >= 2]
    if len(toks) <= 2:
        return f'"{term}"'
    return " AND ".join(toks)

def fetch_count(term, start, end):
    root = api_get({"search_query": f'all:({term_query(term)}) AND submittedDate:[{start} TO {end}]',
                    "max_results":1})
    if root is None: return None
    el = root.find("o:totalResults", OS_NS)
    return int(el.text) if el is not None and el.text else None

def fetch_series(terms=None, months=MONTHS):
    if terms is None:
        terms = json.load(open(TERMS_PATH))
    ranges = month_ranges(months)
    cache = load_cache()
    total = len(terms)*len(ranges); done=0
    for t in terms:
        term = t["term"]
        for ml,s,e in ranges:
            key = f"{term}||{s}"; done+=1
            if cache.get(key) is not None: continue
            cache[key] = fetch_count(term, s, e)
            json.dump(cache, open(CACHE_PATH,"w"), ensure_ascii=False)
            print(f"[{done}/{total}] {term} {ml}: {cache[key]}")
            time.sleep(DELAY)
    print("✓ 시계열 수집 완료")
    return cache

# ── C. 예측 (감쇠 Holt) ────────────────────────────────────────────────────
def holt_fit(y, alpha, beta, phi):
    L = float(y[0]); T = float(y[1]-y[0]) if len(y)>1 else 0.0
    onestep=[None]
    for t in range(1,len(y)):
        f = L + phi*T
        onestep.append(f)
        Ln = alpha*y[t] + (1-alpha)*(L+phi*T)
        T  = beta*(Ln-L) + (1-beta)*phi*T
        L  = Ln
    return L, T, onestep

def holt_forecast(y, h, alpha, beta, phi):
    L,T,_ = holt_fit(y,alpha,beta,phi)
    out=[]; s=0.0
    for i in range(1,h+1):
        s += phi**i
        out.append(max(0.0, L + s*T))
    return out

GRID_A=[0.2,0.4,0.6,0.8]; GRID_B=[0.05,0.1,0.2,0.3]; GRID_P=[0.85,0.92,0.98,1.0]
def grid_search(y):
    best=None; bestsse=float("inf")
    for a in GRID_A:
        for b in GRID_B:
            for p in GRID_P:
                _,_,os_ = holt_fit(y,a,b,p)
                sse=sum((f-y[t])**2 for t,f in enumerate(os_) if f is not None)
                if sse<bestsse: bestsse=sse; best=(a,b,p)
    return best

def backtest(y, h=3):
    if len(y) < h+5: return None
    train=y[:-h]; actual=y[-h:]
    a,b,p = grid_search(train)
    fc = holt_forecast(train,h,a,b,p)
    errs=[abs(f-act)/act for f,act in zip(fc,actual) if act>0]
    return round(sum(errs)/len(errs)*100,1) if errs else None

def slope(ys):
    n=len(ys)
    if n<2: return 0.0
    mx=(n-1)/2; my=sum(ys)/n
    num=sum((i-mx)*(y-my) for i,y in enumerate(ys))
    den=sum((i-mx)**2 for i in range(n))
    return num/den if den else 0.0

# ── analyze ────────────────────────────────────────────────────────────────
def analyze(months=MONTHS):
    terms = json.load(open(TERMS_PATH))
    ranges = month_ranges(months)
    cache = load_cache()
    labels=[r[0] for r in ranges]
    items=[]; mapes=[]
    for t in terms:
        term=t["term"]
        raw=[cache.get(f"{term}||{s}") for _,s,_ in ranges]
        y=[v if isinstance(v,int) else 0 for v in raw]
        if sum(y)<10: continue

        a,b,p = grid_search([float(v) for v in y])
        fc = [round(v,1) for v in holt_forecast([float(v) for v in y],3,a,b,p)]
        mape = backtest([float(v) for v in y],3)
        if mape is not None: mapes.append(mape)

        cur = sum(y[-3:])/3
        prev= sum(y[-6:-3])/3 if sum(y[-6:-3]) else 0
        momentum = round((cur-prev)/prev*100,1) if prev else 0.0
        fc_avg = sum(fc)/3
        pred_growth = round((fc_avg-cur)/cur*100,1) if cur else 0.0
        # 가속도: 최근 절반 기울기 - 이전 절반 기울기
        half=len(y)//2
        accel = round(slope(y[half:]) - slope(y[:half]),2)
        vol = sum(y[-12:]) if len(y)>=12 else sum(y)

        items.append({
            "term":term,"series":y,"forecast":fc,
            "volume":vol,"avg_recent":round(cur,1),
            "momentum":momentum,"pred_growth":pred_growth,
            "accel":accel,"mape":mape,
            "params":{"alpha":a,"beta":b,"phi":p},
        })

    # 정규화 (볼륨은 순위 백분위 → outlier 무관, 사분면에 균등 분산)
    if items:
        order=sorted(items, key=lambda x:x["volume"])
        n=len(order)
        for rank,i in enumerate(order):
            i["vol_norm"]=round(rank/(n-1)*100,1) if n>1 else 50.0
        # 부상 예측 점수: (예측성장 + 모멘텀 + 가속도) × 백테스트 신뢰도
        # 예측이 안 맞는(고MAPE) 용어는 강등 → 신뢰할 수 있는 부상만 상위
        ma=max(abs(i["accel"]) for i in items) or 1
        for i in items:
            raw = 0.5*i["pred_growth"] + 0.3*i["momentum"] + 0.2*(i["accel"]/ma*100)
            conf = 1.0 if i["mape"] is None else max(0.3, 1 - i["mape"]/100)
            i["confidence"] = round(conf,2)
            i["emergence"] = round(raw*conf, 1)

    med_mape = round(sorted(mapes)[len(mapes)//2],1) if mapes else None
    data={
        "generated":datetime.now().strftime("%Y-%m-%d %H:%M"),
        "months":labels,
        "future":_future_labels(labels,3),
        "median_mape":med_mape,
        "n_corpus": json.load(open(CORPUS_PATH)).get("count") if os.path.exists(CORPUS_PATH) else None,
        "items_by_momentum": sorted(items,key=lambda x:-x["momentum"]),
        "items_by_emergence": sorted(items,key=lambda x:-x["emergence"]),
        "items": items,
    }
    json.dump(data, open(DATA_PATH,"w"), ensure_ascii=False, indent=2)
    print(f"✓ 분석 완료: {len(items)}개 용어, 백테스트 중앙 MAPE={med_mape}%")
    return data

def _future_labels(labels, h):
    y,m = map(int, labels[-1].split("-")); out=[]
    for _ in range(h):
        m+=1
        if m==13: m=1; y+=1
        out.append(f"{y:04d}-{m:02d}")
    return out

# ── build ──────────────────────────────────────────────────────────────────
def build(data=None):
    if data is None: data=json.load(open(DATA_PATH))
    from template import TEMPLATE
    open(HTML_PATH,"w").write(TEMPLATE.replace("__DATA__", json.dumps(data,ensure_ascii=False)))
    print(f"✓ 대시보드 생성 → {HTML_PATH}")

# ── CLI ────────────────────────────────────────────────────────────────────
if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "all"
    if cmd=="harvest":
        extract_terms(harvest())
    elif cmd=="discover":   # 빠른 용어품질 점검(시계열 미수집)
        days = int(sys.argv[2]) if len(sys.argv)>2 else 60
        pages = int(sys.argv[3]) if len(sys.argv)>3 else 8
        extract_terms(harvest(days=days, max_pages=pages))
    elif cmd=="extract":    # 캐시 코퍼스로 추출만(API 미사용) — 오프라인 반복용
        extract_terms(json.load(open(CORPUS_PATH)))
    elif cmd=="series":
        fetch_series()
    elif cmd=="analyze":
        build(analyze())
    elif cmd=="build":
        build()
    elif cmd=="all":
        extract_terms(harvest()); fetch_series(); build(analyze())
    elif cmd=="smoke":
        docs=harvest(categories=["cs.AI","cs.CL"], days=20, max_pages=3)
        terms=extract_terms(docs, n=4)
        fetch_series(terms, months=8)
        build(analyze(months=8))
    else:
        print(__doc__)
