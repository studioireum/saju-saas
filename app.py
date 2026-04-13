# -*- coding: utf-8 -*-
"""
사주 SaaS - Flask 서버 v3
lunar_python으로 정확한 만세력 계산
실행: python saju_server.py
환경변수: ANTHROPIC_API_KEY=sk-ant-...
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from lunar_python import Solar
import anthropic

app = Flask(__name__, static_folder='.')
CORS(app)

# ===== 천간지지 데이터 =====
CG = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
JJ = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
CK = ['갑','을','병','정','무','기','경','신','임','계']
JK = ['자','축','인','묘','진','사','오','미','신','유','술','해']
CO = ['木','木','火','火','土','土','金','金','水','水']
JO = ['水','土','木','木','土','火','火','土','金','金','土','水']
CU = ['양','음','양','음','양','음','양','음','양','음']
SAENG = {'木':'火','火':'土','土':'金','金':'水','水':'木'}
KUK   = {'木':'土','土':'水','水':'火','火':'金','金':'木'}
JJMAP = {'子':'癸','丑':'己','寅':'甲','卯':'乙','辰':'戊','巳':'丙',
          '午':'丁','未':'己','申':'庚','酉':'辛','戌':'戊','亥':'壬'}
JDAY  = [4,6,5,6,6,7,7,8,8,7,7,6]

def sipseong(ig, tg):
    io=CO[CG.index(ig)]; to=CO[CG.index(tg)]
    iu=CU[CG.index(ig)]; tu=CU[CG.index(tg)]; s=iu==tu
    if io==to: return '비견' if s else '겁재'
    if SAENG[to]==io: return '정인' if s else '편인'
    if KUK[to]==io:   return '정관' if not s else '편관'
    if SAENG[io]==to: return '식신' if s else '상관'
    if KUK[io]==to:   return '정재' if not s else '편재'
    return '?'

def calc_dws(y, m, d, fwd):
    from datetime import date
    birth = date(y, m, d)
    jday  = JDAY[m-1]
    if fwd:
        if d < jday:
            target = date(y, m, jday)
        else:
            nm = m+1 if m<12 else 1
            ny = y if m<12 else y+1
            target = date(ny, nm, JDAY[nm-1])
        diff = (target - birth).days
    else:
        if d >= jday:
            target = date(y, m, jday)
        else:
            pm = m-1 if m>1 else 12
            py = y if m>1 else y-1
            target = date(py, pm, JDAY[pm-1])
        diff = (birth - target).days
    return max(1, round(diff / 3))

def calc_saju(y, m, d, h, gender):
    """lunar_python 기반 정확한 사주 계산"""
    sol = Solar.fromYmdHms(y, m, d, h, 0, 0)
    lun = sol.getLunar()

    year_gj  = lun.getYearInGanZhi()
    month_gj = lun.getMonthInGanZhi()
    day_gj   = lun.getDayInGanZhi()
    hour_gj  = lun.getTimeInGanZhi()

    def split(gj): return gj[0], gj[1]

    ycg,yjj = split(year_gj)
    mcg,mjj = split(month_gj)
    dcg,djj = split(day_gj)
    hcg,hjj = split(hour_gj)

    P = [{'cg':ycg,'jj':yjj},{'cg':mcg,'jj':mjj},
         {'cg':dcg,'jj':djj},{'cg':hcg,'jj':hjj}]

    OH = {'木':0,'火':0,'土':0,'金':0,'水':0}
    for p in P:
        OH[CO[CG.index(p['cg'])]] += 1
        OH[JO[JJ.index(p['jj'])]] += 1

    NK = ['년','월','일','시']
    SS = {}
    for i,p in enumerate(P):
        if NK[i] != '일':
            SS[NK[i]+'간'] = sipseong(dcg, p['cg'])
        SS[NK[i]+'지'] = sipseong(dcg, JJMAP[p['jj']])

    yum = CU[CG.index(ycg)]
    fwd = (gender=='남' and yum=='양') or (gender=='여' and yum=='음')
    dws = calc_dws(y, m, d, fwd)
    mi, mji = CG.index(mcg), JJ.index(mjj)
    DW = []
    for i in range(1, 9):
        ci = ((mi + (i if fwd else -i)) % 10 + 10) % 10
        ji = ((mji + (i if fwd else -i)) % 12 + 12) % 12
        DW.append({'cg':CG[ci],'jj':JJ[ji],
                   'age':dws+(i-1)*10,'yr':y+dws+(i-1)*10})

    return {'P':P,'ilgan':dcg,'OH':OH,'SS':SS,'DW':DW,'dws':dws}

SYSTEM = """당신은 맹파(盲派) 물상론을 중심으로 정통 명리학을 통합 해석하는 전문가입니다.
천간지지를 살아있는 자연물로 읽습니다: 甲木=큰소나무, 乙木=화초덩굴, 丙火=태양, 丁火=촛불별빛, 戊土=산제방, 己土=논밭, 庚金=도끼바위, 辛金=보석칼날, 壬水=바다강, 癸水=빗물이슬.
해석순서: 1)일간 물상 2)사주 풍경화 묘사 3)오행 결핍·과다 물상화 4)현재 대운 변화 5)직업·재물·관계·건강.
규칙: 마크다운 금지, 산문체 700~900자, 제공된 원국 그대로 사용, 재계산 금지."""

def get_client():
    key = os.environ.get('ANTHROPIC_API_KEY','')
    if not key: return None, 'ANTHROPIC_API_KEY 없음'
    return anthropic.Anthropic(api_key=key), None

@app.route('/')
def index():
    return send_from_directory('.', 'saju_final.html')

@app.route('/api/saju', methods=['POST'])
def saju():
    """사주 계산 API"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error':'입력 없음'}), 400
    try:
        y=int(data['year']); m=int(data['month']); d=int(data['day'])
        h=int(data['hour']); g=data.get('gender','남')
        result = calc_saju(y, m, d, h, g)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """AI 해석 API"""
    client, err = get_client()
    if not client: return jsonify({'error':err}), 401
    data = request.get_json(silent=True)
    if not data or not data.get('messages'):
        return jsonify({'error':'메시지 없음'}), 400
    try:
        resp = client.messages.create(
            model='claude-opus-4-5', max_tokens=2000,
            system=SYSTEM, messages=data['messages']
        )
        return jsonify({'text': resp.content[0].text})
    except anthropic.AuthenticationError:
        return jsonify({'error':'API 키 오류'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    key = os.environ.get('ANTHROPIC_API_KEY','')
    return jsonify({'status':'ok','api_key':'set' if key else 'missing'})

if __name__ == '__main__':
    key = os.environ.get('ANTHROPIC_API_KEY','')
    print("="*50)
    print(f"API 키: {'설정됨' if key else '없음 → set ANTHROPIC_API_KEY=sk-ant-...'}")
    print("접속: http://localhost:5000")
    print("="*50)
    import os as _os
    port = int(_os.environ.get('PORT', 5000))
    app.run(debug=False, port=port, host='0.0.0.0')
