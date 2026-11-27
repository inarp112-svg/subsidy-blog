import os
import json
import re
import time
from datetime import datetime
import requests
from google import genai

# 환경 변수 로드 (GitHub Secrets에서 주입)
GOV24_API_KEY = os.environ["GOV24_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

POSTED_IDS_PATH = "data/posted_ids.json"
POSTS_DIR = "content/posts"
MAX_POSTS_PER_RUN = 3

client = genai.Client(api_key=GEMINI_API_KEY)

def load_posted_ids():
    if not os.path.exists(POSTED_IDS_PATH):
        return []
    with open(POSTED_IDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posted_ids(ids):
    os.makedirs(os.path.dirname(POSTED_IDS_PATH), exist_ok=True)
    with open(POSTED_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)

def fetch_subsidies(page=1, per_page=30):
    url = "https://api.odcloud.kr/api/gov24/v3/serviceList"
    params = {
        "page": page,
        "perPage": per_page,
        "serviceKey": GOV24_API_KEY,
    }
    res = requests.get(url, params=params, timeout=15)
    res.raise_for_status()
    return res.json().get("data", [])

def generate_markdown_post(item):
    today_str = datetime.now().strftime("%Y-%m-%d")
    year_str = datetime.now().strftime("%Y")

    prompt = f"""
당신은 대한민국 정부지원금 전문 에디터입니다. 아래 공공데이터를 바탕으로 검색엔진 최적화(SEO)가 잘 된 블로그 포스팅을 Markdown으로 작성하세요.

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

[작성 규칙]
1. 반드시 아래 YAML Front Matter로 시작하세요.
---
title: "[{year_str}] {item.get('서비스명')} 신청방법, 자격조건, 지원금액 총정리"
date: {today_str}
categories: ["정부지원금"]
tags: ["보조금24", "{item.get('소관기관명')}", "지원금"]
draft: false
---
2. 본문 구성:
   - 도입부: 누가 어떤 혜택을 받을 수 있는지 2~3문장으로 핵심 요약.
   - 핵심 요약 표: 지원대상, 지원내용, 신청기한, 신청방법을 Markdown 표로 정리.
   - 자격 요건 체크리스트: 어려운 행정 용어를 일상어로 풀어 불릿 리스트로 작성.
   - 신청 방법 및 주의사항: 단계별 번호 리스트.
   - 공식 신청 바로가기: 원본 데이터의 상세URL을 링크 버튼 형태로 제공.
3. 원본 데이터에 없는 금액이나 날짜를 절대 지어내지 마세요.
"""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                print(f"서버 혼잡(503) 감지, 15초 후 재시도합니다... ({attempt + 1}/3)")
                time.sleep(15)
            else:
                raise e

def sanitize_filename(text):
    return re.sub(r"[^가-힣a-zA-Z0-9_-]", "-", text)[:50]

def main():
    posted_ids = load_posted_ids()
    items = fetch_subsidies()
    os.makedirs(POSTS_DIR, exist_ok=True)

    count = 0
    for item in items:
        if count >= MAX_POSTS_PER_RUN:
            break

        service_id = item.get("서비스ID")
        if not service_id or service_id in posted_ids:
            continue

        # 지원내용이 너무 부실한 공고는 제외
        if not item.get("지원내용") or len(item.get("지원내용", "")) < 15:
            continue

        md_content = generate_markdown_post(item)
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        slug = sanitize_filename(item.get("서비스명", service_id))
        filename = f"{date_prefix}-{slug}-{service_id}.md"

        with open(os.path.join(POSTS_DIR, filename), "w", encoding="utf-8") as f:
            f.write(md_content)

        posted_ids.append(service_id)
        count += 1
        print(f"발행 완료: {filename}")

    save_posted_ids(posted_ids)

if __name__ == "__main__":
    main()
