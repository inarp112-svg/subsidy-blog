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
MAX_POSTS_PER_RUN = 5   # 1회 실행당 발행할 글 개수
PER_PAGE = 100          # 한 번에 조회할 공고 수
MAX_PAGES = 200         # 무한 루프 방지용 최대 페이지 제한

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

def fetch_subsidies(page=1, per_page=PER_PAGE):
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
당신은 대한민국 정책·복지 분야 전문 에디터입니다. 아래 공공데이터를 바탕으로 독자가 이해하기 쉽게 정리한 정보성 아티클을 Markdown으로 작성하세요.

[원본 데이터]
- 서비스명: {item.get('서비스명')}
- 소관기관: {item.get('소관기관명')}
- 등록일시: {item.get('등록일시')}
- 수정일시: {item.get('수정일시')}
- 지원목적: {item.get('서비스목적요약')}
- 지원대상: {item.get('지원대상')}
- 선정기준: {item.get('선정기준')}
- 지원내용: {item.get('지원내용')}
- 신청방법: {item.get('신청방법')}
- 신청기한: {item.get('신청기한')}
- 상세URL: {item.get('상세조회URL')}

[필수 작성 규칙]
1. 반드시 아래 YAML Front Matter로 시작하세요. 마크다운 코드블록(백틱 3개)으로 감싸지 마세요.
---
title: "[{year_str}] {item.get('서비스명')} 지원 대상 및 신청 방법 정리"
date: {today_str}
categories: ["정부지원금"]
tags: ["보조금24", "{item.get('소관기관명')}", "지원금"]
draft: false
---

2. 문체 및 형식 금지 사항 (매우 중요):
- 본문, 소제목, 링크 어디에도 이모지(💰, ❌, 📝, 🔗, 👉 등)와 특수 기호 아이콘을 절대 사용하지 마세요.
- "안녕하세요", "오늘은 ~에 대해 알아보겠습니다", "주목하세요", "놓치지 마세요", "많은 도움이 되셨길 바랍니다" 같은 뻔한 AI·블로그 상투어를 절대 쓰지 마세요.
- 링크 뒤에 '{{: .btn ...}}' 같은 확장 속성 문법을 절대 붙이지 마세요. 표준 마크다운 링크 '[텍스트](URL)'만 사용하세요.

3. 본문 구성:
- 서두 도입부 (소제목 없이 바로 시작, 3~4문장):
  * 독자의 시선을 끌 수 있도록 실제 생활에서 이 지원금이 절실해지는 구체적인 상황이나 고민을 먼저 짚어주세요.
  * 이 제도가 언제, 어떤 상황에 처한 사람에게 가장 필요한지를 지인이 핵심만 알려주듯 담백하고 자연스러운 구어체 섞인 존댓말(~거든요, ~해 볼 만합니다, ~챙겨보셔야 합니다 등)로 풀어쓰세요.
  * 원본 데이터에 최근 신설·개편된 시점이 명확히 드러나면 자연스럽게 언급하되, 데이터에 없는 최초 도입 연도를 절대 추측해서 지어내지 마세요. 시점 정보가 없다면 "{year_str}년 현재 기준"으로 지금 신청해야 하는 이유에 집중하세요.
- 서두 바로 아래 핵심 한 줄 요약 (인용구 > 사용):
  * > **이런 분께 필요합니다:** (대상과 핵심 혜택을 한 문장으로 명확하게 정리)
- ## 한눈에 보는 핵심 정보: 지원대상, 지원내용, 신청기한, 신청방법, 소관기관을 깔끔한 Markdown 표로 정리.
- ## 지원 대상 및 자격 요건: 행정 용어를 일반 독자가 이해하기 쉬운 일상어로 풀어 설명.
- ## 신청 방법 및 유의사항: 실제 신청 절차를 순서대로 정리하고, 놓치기 쉬운 주의사항을 덧붙임.
- ## 공식 상세 안내: 원본 데이터의 상세URL을 표준 마크다운 링크([보조금24 공식 페이지에서 상세 내용 확인하기
