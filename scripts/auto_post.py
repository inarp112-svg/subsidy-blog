def generate_markdown_post(item):
    today_str = datetime.now().strftime("%Y-%m-%d")
    year_str = datetime.now().strftime("%Y")

    prompt = f"""
당신은 대한민국 정책·복지 분야 전문 에디터입니다. 아래 공공데이터를 바탕으로 독자가 이해하기 쉽게 정리한 정보성 아티클을 Markdown으로 작성하세요.

[원본 데이터]
- 서비스명: {item.get('서비스명')}
- 소관기관: {item.get('소관기관명')}
- 지원목적: {item.get('서비스목적요약')}
- 지원대상: {item.get('지원대상')}
- 선정기준: {item.get('선정기준')}
- 지원내용: {item.get('지원내용')}
- 신청방법: {item.get('신청방법')}
- 신청기한: {item.get('신청기한')}
- 상세URL: {item.get('상세조회URL')}

[필수 작성 규칙]
1. 반드시 아래 YAML Front Matter로 시작하세요. 코드블록(```markdown 등)으로 감싸지 마세요.
---
title: "[{year_str}] {item.get('서비스명')} 지원 대상 및 신청 방법 정리"
date: {today_str}
categories: ["정부지원금"]
tags: ["보조금24", "{item.get('소관기관명')}", "지원금"]
draft: false
---
2. 문체 및 형식 금지 사항 (매우 중요):
- 본문, 소제목, 링크 어디에도 이모지(예: 💰, ❌, 📝, 🔗, 👉 등)와 특수 기호 아이콘을 절대 사용하지 마세요.
- "안녕하세요", "오늘은 ~에 대해 알아보겠습니다", "많은 도움이 되셨길 바랍니다" 같은 뻔한 블로그 인사말과 AI 특유의 과장된 표현을 쓰지 마세요.
- 신문사 정책 해설 기사나 공공 안내문처럼 차분하고 명확한 존댓말(~입니다, ~할 수 있습니다)을 사용하세요.
- 링크 뒤에 '{{: .btn ...}}' 같은 확장 속성 문법을 절대 붙이지 마세요. 반드시 표준 마크다운 링크 '[텍스트](URL)'만 사용하세요.

3. 본문 구성 (소제목은 ## 사용):
- 도입부 (소제목 없이 바로 시작): 이 제도가 어떤 상황에서 도움이 되는지 핵심 내용을 2~3문장으로 자연스럽게 요약.
- ## 한눈에 보는 핵심 정보: 지원대상, 지원내용, 신청기한, 신청방법, 소관기관을 깔끔한 Markdown 표로 정리.
- ## 지원 대상 및 자격 요건: 행정 용어를 일반 독자가 이해하기 쉬운 일상어로 풀어 설명.
- ## 신청 방법 및 유의사항: 실제 신청 절차를 순서대로 정리하고, 놓치기 쉬운 주의사항을 덧붙임.
- ## 공식 상세 안내: 원본 데이터의 상세URL을 표준 마크다운 링크(`[보조금24 공식 페이지에서 상세 내용 확인하기](URL)`)로 제공.

4. 원본 데이터에 없는 금액, 날짜, 조건을 절대 지어내지 마세요.
"""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            text = response.text.strip()
            # 혹시 모를 코드블록 감싸기 및 Kramdown 링크 속성({: ...}) 자동 제거
            text = re.sub(r"^```(?:markdown)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = re.sub(r"\{:[^}]*\}", "", text)
            return text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                print(f"서버 혼잡(503) 감지, 15초 후 재시도합니다... ({attempt + 1}/3)")
                time.sleep(15)
            else:
                raise e
