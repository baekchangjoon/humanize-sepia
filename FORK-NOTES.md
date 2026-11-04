# fork 변경점 (baekchangjoon/humanize-sepia)

원본 `yeomin4242/humanize-sepia@110413b`(0.4.3)을 기술 채널용으로 고친 개인 fork다. 원본 저장소에 PR로 올리지 않는다.

## 바뀐 점

- 스킬 이름을 `humanize-sepia-cj`로 바꿨다. 원본 스킬과 함께 설치해도 충돌하지 않는다.
- 기술 채널을 추가했다: GitHub PR 본문, Jira 티켓, Confluence 해설서, 구현 계획서, 사내 기술 블로그. 이 채널에서는 `references/tech-channels.md` 하나만 읽는다.
- 축약 규칙을 추가했다. 사용자가 축약을 허용하면 중복·부연·자기평가를 덜어 분량을 원문 이하로 맞춘다. 비율을 지정하면 그 비율을 따른다.
- 의미 보호 규칙을 추가했다(cj.2): 결정의 근거, 기존 결함·실패 조건, 주의·경고, 용어 정의, 범위 한정 문장은 축약 대상이 아니다. 분량 목표는 의미 보호보다 아래다.
- 보호 구간을 명시했다: 인라인 코드, 경로, URL, REQ-ID, 이슈 번호, 수치, 체크박스, 상태 기호, 에이전트 지시 블록.
- `scripts/check_preservation.py`를 추가했다. 원문과 결과를 대조해 보호 토큰 누락, 분량 비율, 종결체 혼용을 확인한다. 이를 위해 `allowed-tools`에 `Bash(python3 *)`를 추가했다.

## 점검 스크립트 사용

```bash
python3 skills/humanize-sepia/scripts/check_preservation.py <원문.md> <결과.md> --max-ratio 1.0
python3 -m pytest -q skills/humanize-sepia/tests
```

종료 코드는 0(통과), 1(보호 토큰 누락 또는 분량 초과), 2(사용법 오류)다.
