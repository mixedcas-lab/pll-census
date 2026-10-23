# PLL Census

ISSCC, VLSI, JSSC, CICC, ESSCIRC/ESSERC, A-SSCC, SSC-L, TCAS-I/II, TVLSI에 실린 PLL·주파수 합성기 논문을 모아 보여주는 사이트입니다. MCAS Lab(서울시립대학교 첨단융합학부)에서 운영합니다. 데이터 변환기는 자매 사이트 [ADC Census](https://mixedcas-lab.github.io/adc-census/)에서 다룹니다.

- 사이트: https://mixedcas-lab.github.io/pll-census/
- 데이터 출처: IEEE Xplore API (서지 메타데이터와 링크만 공개, 초록·본문은 올리지 않음)

## 구성

```
index.html, app.js, style.css   사이트 (빌드 과정 없음, GitHub Pages가 그대로 서비스)
data/papers.json                PLL 논문 목록 (빌더가 생성)
data/meta.json                  갱신일, 범위, 집계
data/annotations.csv            검수 값 (사람이 편집)
collector/build.py              adc-census 캐시를 읽어 papers.json 생성 (Python 3.8+, 표준 라이브러리만)
collector/classify.py           PLL 판별, 유형(Integer-N/Fractional-N)·구조·응용 태깅, 수치 추출 규칙
collector/venues.json           시작 연도, 캐시 위치, venue 매칭 규칙
scripts/update.sh               랩 서버 cron용: 재생성 → 커밋 → push
```

## 동작 방식

1. **데이터**: adc-census 수집기가 같은 학회·저널의 전체 논문을 랩 서버 캐시(`~/adc-census/cache/raw`)에 받아 둡니다. 이 저장소는 그 캐시를 읽기만 하므로 IEEE API를 따로 쓰지 않습니다. IEEE Access는 adc-census가 변환기 논문만 받기 때문에 제외했습니다.
2. **분류**: 제목에 PLL, 위상고정루프, 주파수 합성기, 클록 발생기, MDLL 등이 있으면 core, 수신기·송신기 등에 PLL이 들어간 경우나 초록에서만 언급하면 related입니다. 직접 디지털 합성기(DDS)는 제외합니다.
3. **수치**: 제목·초록에서 출력 주파수, 기준 주파수, RMS jitter, 전력, jitter FoM, 기준·분수 스퍼, 위상잡음(오프셋), 락 시간, 공정, 면적을 정규식으로 뽑습니다. FoM<sub>J</sub> = 10 log<sub>10</sub>[(σ<sub>t</sub>/1 s)<sup>2</sup>·(P/1 mW)]이며, 논문에 FoM이 없으면 jitter와 전력으로 계산합니다(≈ 표시).
4. **공개**: cron이 매일 06:47(adc-census 06:17 갱신 뒤) 재생성하고, 바뀐 것이 있으면 커밋·push합니다.

## 그래프

Chart 메뉴: Jitter vs. power(FoM<sub>J</sub> −230~−260 dB 등고선), FoM<sub>J</sub> vs. 출력 주파수, FoM<sub>J</sub> 연도별 추세(누적 최고 3편 평균과 직선 맞춤), Jitter vs. 출력 주파수, 기준 스퍼 vs. FoM<sub>J</sub>, Custom(x·y축 직접 선택, log 전환). 색은 구조, 연도, 출력 주파수, Integer/Fractional 중에서 고릅니다. 채운 점은 검수 값, 테두리 점은 자동 추출 값입니다.

## 검수 값 넣기

GitHub 웹에서 `data/annotations.csv`를 열어 연필 아이콘으로 편집합니다. 수집기를 다시 돌릴 필요 없이 사이트에 즉시 반영됩니다.

| 열 | 내용 |
|---|---|
| `id` | IEEE article number (Xplore 주소 끝의 숫자) |
| `exclude` | `1`이면 목록에서 제외 (오탐) |
| `type` | `Integer-N` 또는 `Fractional-N` |
| `arch`, `app` | 여러 개면 `;`로 구분 (예: `Digital/ADPLL;DTC-based`) |
| `f`, `fref`, `pn_off` | Hz (`5.6G`, `100M`, `1M`) |
| `jitter`, `lock` | s (`85f` = 85 fs, `20u` = 20 µs) |
| `p` | W (`9.4m`) |
| `node`, `area` | nm, mm² |
| `fom` | dB (음수, 예: `-250.1`) |
| `spur`, `fspur`, `pn` | dBc, dBc, dBc/Hz (음수) |
| `cal` | `1`이면 보정 기법 사용, `0`이면 미사용 (비우면 자동 판정) |
| `note`, `by` | 메모, 검수자. 메모는 목록에 표시되고 검색창에서도 찾을 수 있습니다 |

## 랩 서버 설정 (1회)

adc-census가 같은 서버에 설정되어 있어야 합니다(`~/adc-census/cache/raw`).

```bash
ssh-keygen -t ed25519 -f ~/.ssh/pll_census -N "" -C "pll-census@lab-server"   # 공개키를 저장소 Deploy keys에 쓰기 권한으로 등록
cat >> ~/.ssh/config <<'CFG'
Host github-pll-census
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/pll_census
  IdentitiesOnly yes
CFG
git clone github-pll-census:mixedcas-lab/pll-census.git ~/pll-census
cd ~/pll-census && git config user.name "MCAS Lab bot" && git config user.email "연구실-메일-주소"
mkdir -p logs
( crontab -l; echo "47 6 * * * PYTHON=$(command -v python3) $HOME/pll-census/scripts/update.sh >> $HOME/pll-census/logs/update.log 2>&1" ) | crontab -
```

GitHub Pages: 저장소 **Settings → Pages**에서 Source를 **Deploy from a branch**, Branch를 **main / (root)**로 지정합니다.

### 수치 수정 요청

- 사이트의 각 논문 아래 **Report a fix**를 누르면 GitHub 이슈 작성 화면이 열립니다. 논문 id, 현재 값과 출처, annotations.csv 행 형식이 미리 채워져 있으니 고칠 항목·값·근거(표·그림·쪽)만 적으면 됩니다(GitHub 계정 필요).
- 연구실은 이슈를 확인해 `data/annotations.csv`에 행을 추가하고 이슈를 닫습니다. 저장소 쓰기 권한이 있으면 annotations.csv를 직접 고쳐도 됩니다.
- PLL이 송수신기 등의 블록이거나 초록에서만 언급된 논문(related)은 논문의 수치가 PLL 값이 아니므로 자동·AI 수치를 표시하지 않고 "—"로 둡니다. 사람이 검수한 값은 표시합니다.

### 값의 출처와 삭제

- 사이트는 값마다 출처를 표시합니다: `T` 제목, `A` 초록(둘 다 정규식 자동 추출, 회색), `AI` AI 도구 추출(보라색 기울임, 미검수), `✓` 연구실 검수(진한 색).
- annotations.csv의 행은 기본적으로 **사람 검수**로 처리합니다. `by` 열에 Codex·GPT·Claude 같은 AI 도구 이름이 있거나 `source` 열이 `ai`이면 **AI 추출**로 처리합니다.
- 값이 서로 다를 때 우선순위: 사람 검수 > AI 추출 > 정규식(제목·초록). AI 값은 더 높은 출처를 덮어쓰지 않고, 다르면 목록에 `Review` 태그를 붙입니다. AI 행의 메모는 표시하지 않습니다.
- 칸을 비우면 기존 값을 유지합니다. **잘못된 자동값을 지우려면 `-`(또는 `NA`)** 를 넣습니다. 사이트에는 "—"로 표시됩니다.
- 사이트의 Values 필터로 검수된 값만 보거나, 그래프에서 검수 값(채운 점)·AI 값(점선 테두리)·자동 값(테두리)을 구분해 볼 수 있습니다.

### 태그 입력 요령

- `arch`, `app`을 채우면 자동 태그를 **대체**합니다. 자동 태그 중 맞는 것도 함께 적으세요.
- 대소문자·하이픈·공백은 구분하지 않고, 자주 쓰는 약칭도 인식합니다: `adpll`→Digital/ADPLL, `sspll`→Sampling, `cp`→Charge-pump, `il`→Injection-locked, `dtc`→DTC-based, `fmcw`→Radar/FMCW.
- `cal` 열이 헤더에 없으면 헤더 줄 끝에 `,cal`을 붙이고 쓰면 됩니다(열 순서는 상관없음).

## 참고

- IEEE Xplore API 이용약관을 따릅니다. 초록과 본문은 공개하지 않고, 서지 정보와 Xplore 링크만 제공합니다.
- 자동 추출 수치는 오류가 있을 수 있습니다. jitter는 논문마다 적분 대역이 다르니 비교 시 원문을 확인하세요.
