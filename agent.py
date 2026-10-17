import json
import os
import subprocess
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
                "在作業系統的終端機執行指定的 Shell 指令（例如跑測試、查看目錄檔案等）。"
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
            "你是一個擁有終端機操作權限的高級工程師 AI 代理。"
            "當需要執行指令時，請透過工具呼叫來完成任務。請一步一步執行，直到完成使用者的要求為止。"
        ),
    },
    {
        "role": "user",
        "content": (
            "請幫我檢查目前這個專案資料夾底下有哪些檔案，並執行一下"
            " test_code.py 看看目前的執行狀況。"
        ),
    },
]

print("--- 🤖 啟動連續迴圈 AI 代理 ---")

# 進入連續對話迴圈（最多執行 3 次互動，避免無限迴圈）
for turn in range(3):
  print(f"\n--- 迴圈第 {turn + 1} 次思考 ---")

  response = client.chat.completions.create(
      model="qwen2.5-coder:7b", messages=messages, tools=tools, tool_choice="auto"
  )

  response_message = response.choices[0].message
  content_to_check = response_message.content or ""
  messages.append(response_message)

  command_to_run = None

  # 檢查標準 tool_calls
  if response_message.tool_calls:
    tool_call = response_message.tool_calls[0]
    if tool_call.function.name == "run_terminal_command":
      args = json.loads(tool_call.function.arguments)
      command_to_run = args.get("command")

  # 容錯機制：從文字中抓 JSON 指令
  elif "run_terminal_command" in content_to_check or "python test_code.py" in content_to_check:
    try:
      if "{" in content_to_check and "}" in content_to_check:
        start_idx = content_to_check.find("{")
        end_idx = content_to_check.rfind("}") + 1
        json_str = content_to_check[start_idx:end_idx]
        parsed_json = json.loads(json_str)
        if "arguments" in parsed_json and "command" in parsed_json["arguments"]:
          command_to_run = parsed_json["arguments"]["command"]
      # 如果模型直接用文字寫了指令
      elif "python test_code.py" in content_to_check:
        command_to_run = "python test_code.py"
    except Exception:
      pass

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
    # 如果 AI 沒有要求執行指令，代表它已經回答完畢了
    print("\n--- 💡 AI 的最終回覆 ---")
    print(content_to_check)
    break