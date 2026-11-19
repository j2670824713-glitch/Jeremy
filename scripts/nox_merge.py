# Merge all parsed Nox ranking pages, keep Chinese-language channels with >=300k subs,
# and derive estimates. Output: JSON + CSV.
import glob, json, os, re, sys, csv
sys.path.insert(0, os.path.dirname(__file__))
from nox_parse import parse

CJK = re.compile(r'[一-鿿]')
FOREIGN = re.compile(r'[ぁ-ゖァ-ヺ가-힯฀-๿ሀ-፿]')  # kana (not ・), hangul, thai, ethiopic
EXCLUDE = {'YASU Road', 'ሴንቶኩጂ ዊሃን ፕራሳሳና      เซ็นโตกุจิวิหาร ประสาร', 'The Weeknd', 'Kenshi Yonezu  米津玄師', 'Illslick thelegandary', 'CharlesPyro Fireworks'}
ORG = re.compile(r'official|官方|TV\b|TV |電視|电视|卫视|衛視|iQIYI|爱奇艺|愛奇藝|Tencent|YOUKU|優酷|优酷|CCTV|SMG|MangoTV|芒果|HunanTV|JiangsuTV|Zhejiang|'
                 r'China Daily|中国日报|NEWS|新聞|新闻|唱片|RECORDS|Music|音樂|Drama|劇場|剧场|戲劇|戏剧|短剧|微短剧|Theater|MOVIE|Movie|Cinema|影视|影視|'
                 r'映画|Media|傳媒|传媒|Network|Huace|华策|HUACE|MZTV|Croton|Animation|动漫|動漫|Ani-One|Muse木棉花|Nintendo|McDonalds|兒歌|儿歌|寶寶巴士|'
                 r'Bebefinn|LiaChaCha|Masha|瑪莎|玛莎|熊出没|Boonie|迷你特工|Miniforce|珀利|Vidol|NewShowBiz|ShanghaiEye|台灣達人秀|WayV|TFBOYS|MIRROR|'
                 r'挑战不可能|百家讲坛|春晚|爱情保卫战|Keep Running|捷成|九州快看|华剧|華劇|劇屋|剧集|Cdrama|Sparking Sis|YULE|Wonderful drama|甜寵小劇場|'
                 r'兄弟劇場|追剧|追劇|劇癮|大劇|EHPMusic|福茂|相信音樂|ZEN MAHJONG|STR Network|台灣地震|YOYOTV|变形警车|功夫侦探所|云阙|豆芽', re.I)

d = sys.argv[1]
chans = {}
for f in sorted(glob.glob(os.path.join(d, '*.html'))):
    base = os.path.basename(f)
    region = base.split('-')[2]
    period = 'monthly' if base.endswith('monthly.html') else 'weekly'
    try:
        rows = parse(f)
    except Exception as e:
        print('parse fail', f, e, file=sys.stderr); continue
    for r in rows:
        cid = r.get('channelId')
        if not cid:
            continue
        v = r.get('video') or {}
        rec = chans.setdefault(cid, {'id': cid, 'regions': set()})
        rec['regions'].add(region)
        for k in ('title', 'alias', 'followers', 'totalViews', 'avgViews', 'engagementRate', 'ytbCategories', 'shortsVideoPercent'):
            if r.get(k) is not None:
                rec[k] = r[k]
        if r.get('followersDiff') is not None:
            rec['g_' + period] = r['followersDiff']
        if v.get('title'):
            rec['lastVideoTitle'] = v.get('title'); rec['lastPub'] = v.get('pubTime')

YTD_DAYS = 323  # 2026-01-01 .. 2026-11-19
CAT = {1: '电影动画', 2: '汽车', 10: '音乐', 15: '宠物动物', 17: '体育', 19: '旅游', 20: '游戏', 22: '人物博客', 23: '喜剧',
       24: '娱乐', 25: '新闻政治', 26: '生活技巧', 27: '教育', 28: '科技', 29: '公益', 34: '喜剧', 43: '节目', 44: '预告片'}
REG = {'cn': '中国大陆', 'tw': '台湾', 'hk': '香港', 'my': '马来西亚', 'sg': '新加坡', 'us': '美国', 'jp': '日本', 'ca': '加拿大',
       'au': '澳大利亚', 'gb': '英国', 'kr': '韩国', 'th': '泰国'}
out = []
for c in chans.values():
    name = c.get('title') or ''
    vt = c.get('lastVideoTitle') or ''
    if name in EXCLUDE or (c.get('followers') or 0) < 300000:
        continue
    if FOREIGN.search(vt):
        continue  # latest video in Japanese/Korean/Thai -> not a Chinese-language channel
    zh = CJK.search(vt) or (CJK.search(name) and not FOREIGN.search(name))
    if not zh:
        continue
    subs = c['followers']; v30 = c.get('totalViews'); avg = c.get('avgViews')
    gw = c.get('g_weekly'); gm = c.get('g_monthly')
    # subscriber growth: prefer monthly figure, else weekly*30/7
    g = gw if gw is not None else gm  # weekly and monthly pages carry the same (weekly) data
    gw = g
    if gw is not None:
        sub30 = subs * gw / (1 + gw) * 30 / 7
    else:
        sub30 = None
    sp = c.get('shortsVideoPercent')
    row = {
        'channel': name, 'id': c['id'], 'url': 'https://www.youtube.com/channel/' + c['id'],
        'region': '/'.join(REG.get(x, x) for x in sorted(c['regions'])),
        'category': '/'.join(CAT.get(x, str(x)) for x in (c.get('ytbCategories') or [])),
        'type': '机构/官方' if ORG.search(name) else '个人/工作室',
        'subs': subs,
        'views30': v30, 'avgViews': avg,
        'videos30': round(v30 / avg) if v30 and avg else None,
        'views2026_est': round(v30 * YTD_DAYS / 30) if v30 else None,
        'rev30_low': round(v30 / 1000 * 0.25) if v30 else None,
        'rev30_high': round(v30 / 1000 * 4) if v30 else None,
        'rev2026_low': round(v30 * YTD_DAYS / 30 / 1000 * 0.25) if v30 else None,
        'rev2026_high': round(v30 * YTD_DAYS / 30 / 1000 * 4) if v30 else None,
        # Shorts-adjusted creator revenue: Shorts RPM $0.02-0.08, long-form RPM $0.5-3.0 per 1000 views
        'revadj2026_low': round(v30 * YTD_DAYS / 30 / 1000 * (sp * 0.02 + (1 - sp) * 0.5)) if v30 and sp is not None else None,
        'revadj2026_high': round(v30 * YTD_DAYS / 30 / 1000 * (sp * 0.08 + (1 - sp) * 3.0)) if v30 and sp is not None else None,
        'growth_week_pct': round(gw * 100, 2) if gw is not None else None,
        'subs30_est': round(sub30) if sub30 is not None else None,
        'subs2026_est': round(sub30 * YTD_DAYS / 30) if sub30 is not None else None,
        'er_pct': round(c['engagementRate'] * 100, 2) if c.get('engagementRate') is not None else None,
        'shorts_pct': round(c['shortsVideoPercent'] * 100) if c.get('shortsVideoPercent') is not None else None,
        'lastVideo': vt,
    }
    out.append(row)
out.sort(key=lambda x: -x['subs'])
for i, r in enumerate(out, 1):
    r['rank'] = i
json.dump(out, open(sys.argv[2] + '.json', 'w'), ensure_ascii=False)
cols = ['rank', 'channel', 'type', 'region', 'category', 'subs', 'views30', 'avgViews', 'videos30', 'views2026_est',
        'rev30_low', 'rev30_high', 'rev2026_low', 'rev2026_high', 'revadj2026_low', 'revadj2026_high', 'growth_week_pct', 'subs30_est',
        'subs2026_est', 'er_pct', 'shorts_pct', 'url']
hdr = ['排名', '频道', '类型(自动判断)', '榜单地区', '分类', '订阅数', '近30天新视频播放', '平均每支播放', '近30天发片数(推算)',
       '2026年播放(估算,1/1-11/19)', '近30天收入低(USD)', '近30天收入高(USD)', '2026收入低(USD,估算)', '2026收入高(USD,估算)', '2026收入低-Shorts校正(USD)', '2026收入高-Shorts校正(USD)',
       '周订阅增长%(Nox,精度0.1%)', '近30天新增订阅(估算)', '2026新增订阅(估算)', '互动率%', 'Shorts占比%', '链接']
with open(sys.argv[2] + '.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh); w.writerow(hdr)
    for r in out:
        w.writerow(['' if r[k] is None else r[k] for k in cols])
print('kept', len(out), 'with views', sum(1 for r in out if r['views30']), 'orgs', sum(1 for r in out if r['type'] != '个人/工作室'), file=sys.stderr)
