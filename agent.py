# -*- coding: utf-8 -*-
import sys
import io

# 強制將標準輸出（stdout）和標準錯誤（stderr）改為 UTF-8 編碼，防止中文亂碼
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import subprocess
import json
from openai import OpenAI

# 1. 連線到本機 Ollama
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


# 2. 定義終端機工具
def run_terminal_command(command):
  print(f"\n⚡ [Agent 正在執行終端機指令]: {command}")

  if "ls" in command and "dir" not in command:
    command = "dir"

  try:
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, errors="ignore"
    )
    output = (result.stdout or "") + (result.stderr or "")
    return output if output.strip() else "指令執行成功，但沒有任何輸出。"
  except Exception as e:
    return f"執行指令時發生錯誤: {str(e)}"


tools = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": (
                "在終端機執行指定的 Shell 指令，可用於執行 git status, git diff,"
                " git commit 等。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要執行的終端機指令",
                    }
                },
                "required": ["command"],
            },
        },
    }
]

messages = [
    {
        "role": "system",
        "content": (
            "你是一個專業的 Git 助手與高級工程師 AI 代理。"
            "請先檢查 `git status`。"
            "如果檔案尚未 add，請執行 `git add .`；"
            "如果已經準備好，請務必使用【雙引號】執行 git commit，例如：git commit -m \"fix: update agent.py logic\"。"
            "【嚴格規定】Commit 訊息必須全部使用英文，絕對不准使用中文或單引號，以免終端機解析錯誤。"
            "絕對不准自己發明或想像其他工具名稱。"
        ),
    },
    {
        "role": "user",
        "content": (
            "請幫我檢查目前專案的變更，並自動幫我完成 git add 與 git commit"
            " 的工作。"
        ),
    },
]

print("--- 🤖 啟動全自動 Git 代理 ---")

# 進入連續對話迴圈（擴大到 4 次，讓它有空間做完 status -> diff -> commit）
for turn in range(4):
  print(f"\n--- 迴圈第 {turn + 1} 次思考 ---")

  response = client.chat.completions.create(
      model="qwen2.5-coder:7b", messages=messages, tools=tools, tool_choice="auto"
  )

  response_message = response.choices[0].message
  content_to_check = response_message.content or ""
  messages.append(response_message)

  command_to_run = None

  # 1. 檢查標準 tool_calls
  if response_message.tool_calls:
    tool_call = response_message.tool_calls[0]
    if tool_call.function.name == "run_terminal_command":
      args = json.loads(tool_call.function.arguments)
      command_to_run = args.get("command")

  # 2. 萬能容錯機制：攔截文字中的 JSON（支援單引號或雙引號）
  elif "run_terminal_command" in content_to_check or "command" in content_to_check:
    try:
      start_idx = content_to_check.find("{")
      end_idx = content_to_check.rfind("}") + 1
      if start_idx != -1 and end_idx != 0:
        json_str = content_to_check[start_idx:end_idx]
        # 兼容處理模型可能用單引號包覆字串的問題
        try:
          parsed_json = json.loads(json_str)
        except json.JSONDecodeError:
          # 如果標準 json.loads 失敗，嘗試把外層或內層的單引號轉成雙引號
          fixed_json_str = json_str.replace("'", '"')
          parsed_json = json.loads(fixed_json_str)

        if "arguments" in parsed_json and "command" in parsed_json["arguments"]:
          command_to_run = parsed_json["arguments"]["command"]
    except Exception as e:
      print(f"解析指令時發生例外狀況: {e}")

  # 如果成功抓到指令，執行它並把結果餵回給模型
  if command_to_run:
    tool_output = run_terminal_command(command_to_run)
    print(f"🔧 工具執行結果：\n{tool_output}")

    messages.append({
        "role": "tool",
        "tool_call_id": (
            response_message.tool_calls[0].id
            if response_message.tool_calls
            else "fallback_id"
        ),
        "name": "run_terminal_command",
        "content": tool_output,
    })
  else:
    # 如果 AI 沒有要求執行指令，代表任務已經全數完成
    print("\n--- 💡 AI 的最終回覆 ---")
    print(content_to_check)
    break