;; ====================================================
;; 文件：news-simulation-simple.nlogo
;; 描述：纯文件交换式通信（无外部命令调用，兼容所有NetLogo 6.2.1/7.0）
;; 适配说明：无需shell/run命令，依赖Python轮询脚本处理HTTP请求
;; ====================================================

;; ---------- 全局变量 ----------
globals [
  api-base-url     ;; API服务器地址
  api-status
  last-question
  script-running   ;; 标记Python轮询脚本是否已启动（仅做提示）
]

;; ---------- 智能体品种 ----------
breed [medias media]
medias-own [
  name
  country
  question
]

;; ---------- 初始化 ----------
to setup
  clear-all
  reset-ticks

  ;; 初始化状态变量
  set api-base-url ""
  set api-status "未连接"
  set last-question "暂无"
  set script-running false

  ;; 创建媒体智能体
  create-medias 3 [
    set shape "person"
    set color blue
    set size 1.5
    setxy random-xcor random-ycor

    if (who = 0) [ set name "BBC" set country "英国" ]
    if (who = 1) [ set name "新华社" set country "中国" ]
    if (who = 2) [ set name "CNN" set country "美国" ]

    set label name
    set question ""
  ]

  ;; 输出初始化完成信息（关键提示：启动Python轮询脚本）
  output-print "=== 系统初始化完成 ==="
  output-print "⚠️  请先启动Python轮询客户端：python http_client_polling.py"
  output-print "2. 在浏览器访问 http://localhost:8000/docs 能打开"
  output-print "然后点击 '测试API连接'"
end

;; ---------- 通用文件交换请求函数（无外部命令调用） ----------
to-report send-file-request [request-type url json-data]
  ;; 1. 清理旧文件，避免干扰
  let temp-request "temp_request.txt"
  let temp-response "temp_response.txt"
  let temp-error "temp_error.txt"

  foreach (list temp-request temp-response temp-error) [
    file -> if file-exists? file [ file-delete file ]
  ]

  ;; 2. 写入请求文件（供Python轮询脚本检测）
  file-open temp-request
  let lines (list request-type url json-data)
  if length lines > 0 [
    foreach lines [ line -> file-print line ]
  ]
  file-close

  output-print (word "已写入请求文件，等待处理：" request-type " " url)

  ;; 3. 轮询等待处理结果（超时10秒）
  let timeout 0
  let max-timeout 20  ;; 对应Python轮询间隔0.5秒，总超时10秒
  let result []

  while [timeout < max-timeout and not (file-exists? temp-response or file-exists? temp-error)] [
    wait 0.5
    set timeout timeout + 1
  ]

  ;; 4. 读取处理结果
  carefully [
    ; 第一层条件：检查响应文件
    if file-exists? temp-response [
      ;; 读取成功响应
      file-open temp-response
      let response-line file-read-line
      file-close
      ;; 解析响应
      set result parse-simple-response response-line
    ]
    ; 第二层条件：检查错误文件
    if (not file-exists? temp-response) and file-exists? temp-error [
      ;; 读取错误信息
      file-open temp-error
      let error-msg file-read-line
      file-close
      set result ["error"  "success" false]
    ]
    ; 第三层条件：超时
    if (not file-exists? temp-response) and (not file-exists? temp-error) [
      ;; 请求超时
      set result ["error" "请求超时，Python脚本未响应" "success" false]
    ]
  ] [
    ; carefully捕获的异常处理
    set result ["error" ( "文件读取失败：" ) "success" false]
  ]

  ;; 5. 清理临时文件
  foreach (list temp-request temp-response temp-error) [
    file -> if file-exists? file [ file-delete file ]
  ]

  report result
end

;; ---------- 简单响应解析 ----------
to-report parse-simple-response [response-line]
  let parts split-string response-line "|"

  if length parts >= 2 [
    let code item 0 parts
    let message item 1 parts

    if code = "200" [
      report ["status"  "content"  "success" true]
    ]

    report ["error"  "success" false]
  ]

  report ["error" ( "无法解析响应: " ) "success" false]
end

;; ---------- 分割字符串工具函数（修正start偏移问题，兼容NetLogo 6.2.1/7.0） ----------
to-report split-string [str delimiter]
  let result []
  let start 0  ;; 查找起始偏移位置
  let str-length length str  ;; 缓存字符串总长度，避免重复计算
  let delimiter-length length delimiter  ;; 缓存分隔符长度（兼容多字符分隔符）

  ;; 边界判断：空字符串或空分隔符直接返回原字符串
  if str = "" or delimiter = "" [
    report (list str)
  ]

  while [start < str-length] [
    ;; 关键修正：通过截取子字符串实现「从start位置开始查找」
    ;; 1. 截取从start到末尾的子字符串
    let sub-str substring str start str-length
    ;; 2. 在子字符串中查找分隔符（使用position合法的双参数格式）
    let sub-end-pos position delimiter sub-str
    ;; 3. 转换为原字符串中的索引位置
    let end-pos false

    if sub-end-pos != false [
      set end-pos start + sub-end-pos
    ]

    ;; 4. 处理找到/未找到分隔符的两种场景（改用独立单分支if，无格式陷阱）
    if end-pos != false [
      ;; 找到分隔符：提取子串并添加到结果列表
      set result lput (substring str start end-pos) result
      ;; 5. 更新下一次查找的起始位置（跳过当前分隔符）
      set start end-pos + delimiter-length
    ]

    ;; 用独立的"if not"替代双分支，避免格式报错，逻辑更清晰
    if end-pos = false [
      ;; 未找到分隔符：提取剩余字符串并退出循环
      set result lput (substring str start str-length) result
      set start str-length  ;; 终止while循环
    ]
  ]

  ;; 6. 返回最终分割结果
  report result
end

;; ---------- 测试API连接 ----------
to test-api-connection
  output-print "--- 开始测试API连接 ---"

  if api-base-url = "" [
    set api-base-url "http://localhost:8000"
    output-print (word "使用默认API地址: " api-base-url)
  ]

  let url (word api-base-url "/health")
  let result send-file-request "GET" url ""

  if (item 3 result = true) [
    set api-status "连接正常"
    output-print "✅ API连接测试成功！"

    let content item 5 result
    if content != false and content != "" [
      output-print (word "   服务器响应: " content)
    ]
  ]
  if (item 3 result = false)[
    set api-status "连接失败"
    let error-msg item 3 result
    output-print (word "❌ 连接失败: " error-msg)
    output-print "请检查:"
    output-print "1. Python API服务器是否运行？"
    output-print "2. Python轮询客户端是否启动？"
    output-print "3. 防火墙是否阻止了本地端口8000？"
  ]
end

;; ---------- 让媒体生成提问内容 ----------
to ask-one-media
  output-print "--- 开始生成媒体提问 ---"

  if api-status != "连接正常" [
    output-print "❌ 请先点击'测试API连接'确保连接正常"
    stop
  ]

  let reporter one-of medias with [name = "BBC"]
  if reporter = nobody [
    set reporter one-of medias
  ]

  ask reporter [
    output-print (word "【" name " (" country ")】正在生成问题...")

    let topic "朝韩关系紧张"
    let request-data (word "{\"agent_type\": \"media\", \"agent_id\": \"" name "\", \"topic\": \"" topic "\", \"attributes\": {\"country\": \"" country "\", \"name\": \"" name "\"}}")

    let url (word api-base-url "/generate")
    let result send-file-request "POST" url request-data

    if (item 3 result = true) [
      let content item 5 result
      let question-text extract-question-from-json content
      set question question-text
      set last-question question-text

      output-print "✅ 问题生成成功！"
      output-print (word "   【" name "】问：" question)

      set color yellow
      wait 0.5
      set color blue
    ]
    if (item 3 result = false) [
      let error-msg item 3 result
      output-print (word "❌ 生成失败: " error-msg)
    ]
  ]

  output-print "--- 媒体提问完成 ---"
end

;; ---------- 从JSON响应中提取问题内容 ----------
to-report extract-question-from-json [json-text]
  ; 空内容判断
  if json-text = false or json-text = "" [
    report "无内容"
  ]

  ; 1. 查找"content":"的位置（修正转义符与赋值格式）
  let content-start position "\"content\":\"" json-text
  ; 若未找到，查找"content": "的位置
  if content-start = false [
    set content-start position "\"content\": \"" json-text
  ]

  ; 提取content内容
  if content-start != false [
    let quote-start content-start + length "\"content\":\""
    ; 找到内容的起始引号
    while [quote-start < length json-text and item quote-start json-text != "\""] [
      set quote-start quote-start + 1
    ]
    ; 找到内容的结束引号（处理转义，无stop）
    let quote-end quote-start
    let in-escape false
    let found-end false

    while [quote-end < length json-text and not found-end] [
      let ch item quote-end json-text
      if ch = "\\" [
        set in-escape true
        set quote-end quote-end + 1
      ]
      if ch != "\\" [
        if ch = "\"" and not in-escape [
          set found-end true
        ]
        set in-escape false
        set quote-end quote-end + 1
      ]
    ]
    ; 提取内容
    if quote-end > quote-start [
      report substring json-text quote-start quote-end
    ]
  ]

  ; 无法提取时返回前100字符
  if length json-text > 100 [
    report (word (substring json-text 0 100) "...")
  ]
  report json-text
end

;; ---------- 一键快速测试 ----------
to run-quick-test
  output-print ">>> 开始一键快速测试 <<<"
  setup
  wait 0.5
  test-api-connection
  wait 0.5
  ask-one-media
  output-print ">>> 一键测试完成 <<<"
end

;; ---------- 系统重置 ----------
to reset-all
  clear-all
  reset-ticks
  set api-status "未连接"
  set last-question "暂无"
  output-print "系统已重置，可重新进行初始化"
end
@#$#@#$#@
GRAPHICS-WINDOW
1244
358
1681
796
-1
-1
13.0
1
10
1
1
1
0
1
1
1
-16
16
-16
16
0
0
1
ticks
30.0

BUTTON
89
15
176
48
test-api
test-api-connection
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
191
15
312
48
ask-one-media
ask-one-media
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

MONITOR
31
286
113
331
api-status
api-status
0
1
11

MONITOR
33
347
136
392
last-question
last-question
0
1
11

OUTPUT
45
420
285
474
12

@#$#@#$#@
## WHAT IS IT?

(a general understanding of what the model is trying to show or explain)

## HOW IT WORKS

(what rules the agents use to create the overall behavior of the model)

## HOW TO USE IT

(how to use the model, including a description of each of the items in the Interface tab)

## THINGS TO NOTICE

(suggested things for the user to notice while running the model)

## THINGS TO TRY

(suggested things for the user to try to do (move sliders, switches, etc.) with the model)

## EXTENDING THE MODEL

(suggested things to add or change in the Code tab to make the model more complicated, detailed, accurate, etc.)

## NETLOGO FEATURES

(interesting or unusual features of NetLogo that the model uses, particularly in the Code tab; or where workarounds were needed for missing features)

## RELATED MODELS

(models in the NetLogo Models Library and elsewhere which are of related interest)

## CREDITS AND REFERENCES

(a reference to the model's URL on the web if it has one, as well as any other necessary credits, citations, and links)
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.2.1
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
