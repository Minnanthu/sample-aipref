#!/usr/bin/env python3
"""
Smoke test: OpenAI互換APIのストリーミング疎通確認
1リクエストを送信して接続とストリーミング応答を確認する
"""

import os
import sys
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

def main():
    # 環境変数の取得
    url = os.getenv("AIPERF_URL", "").strip().rstrip("/")
    model = os.getenv("MODEL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if not model:
        print("Error: MODEL is not set in .env", file=sys.stderr)
        sys.exit(1)
    
    # OpenAI APIを使用する場合（AIPERF_URLが空またはOpenAIのURLの場合）
    use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
    
    if use_openai_api:
        if not api_key:
            print("Error: OPENAI_API_KEY is required when using OpenAI API", file=sys.stderr)
            sys.exit(1)
        url = None  # OpenAI SDKのデフォルトを使用
        endpoint = "https://api.openai.com/v1/chat/completions"
    else:
        # URLの正規化（http://が無い場合は追加）
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        endpoint = f"{url}/v1/chat/completions"
    
    print(f"Testing connection to: {endpoint}")
    print(f"Model: {model}")
    print("-" * 60)
    
    try:
        from openai import OpenAI
        
        # クライアントの作成
        if use_openai_api:
            # OpenAI APIを使用（api_keyのみ指定、base_urlはデフォルト）
            client_kwargs = {
                "api_key": api_key,
            }
        else:
            # カスタムOpenAI互換APIを使用
            client_kwargs = {
                "base_url": url,
                "api_key": api_key if api_key else "dummy-key",  # 認証不要な場合はダミー
            }
        client = OpenAI(**client_kwargs)
        
        # ストリーミングリクエストの送信
        print("Sending streaming request...")
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello! Please respond with a short message."}
            ],
            stream=True,
            max_tokens=50,
        )
        
        # ストリーミング応答の受信
        first_token_received = False
        token_count = 0
        full_response = ""
        
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    if not first_token_received:
                        print("\n✓ First token received (TTFT OK)")
                        first_token_received = True
                    print(delta.content, end="", flush=True)
                    full_response += delta.content
                    token_count += 1
        
        print("\n" + "-" * 60)
        print(f"✓ Streaming completed successfully")
        print(f"  Tokens received: {token_count}")
        print(f"  Response length: {len(full_response)} chars")
        print("\n✓ Smoke test passed!")
        return 0
        
    except ImportError:
        print("Error: openai package not installed. Run 'make setup' first.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error occurred: {type(e).__name__}: {e}", file=sys.stderr)
        print("\nTroubleshooting:", file=sys.stderr)
        print("  1. Check if AIPERF_URL is correct", file=sys.stderr)
        print("  2. Check if MODEL name matches the server", file=sys.stderr)
        print("  3. Check if OPENAI_API_KEY is set (if required)", file=sys.stderr)
        print("  4. Check network connectivity to the server", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
