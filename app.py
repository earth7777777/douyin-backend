# app.py
# 简易后端：Flask + 内存任务队列（用于本地调试 / 前端联调）
# 运行：pip install flask flask-cors
# 然后：python app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading, time, uuid

app = Flask(__name__)
CORS(app)  # 开发时允许跨域，生产请加安全限制

# 内存任务存储（MVP 用）
# task_id -> {status, progress, result, created_at}
TASKS = {}

# ========= 可替换的“抓评论”函数 =========
def fetch_comments(aweme_id: str, max_items: int = 50, timeout: int = 10):
    """
    返回：List[{"id": "...", "text": "..."}]
    当前为模拟实现（便于联调）。以后把这里替换为企业API/自建抓取器。
    只要保持返回结构不变，后面分析逻辑就不用改。
    """
    sample_comments = [
        {"id": "c1", "text": "小姐姐这个妆容太美了！"},
        {"id": "c2", "text": "我觉得不太行，声音太小。"},
        {"id": "c3", "text": "超喜欢！支持一下～"},
        {"id": "c4", "text": "穿搭太好看了，哪里买的裙子？"},
        {"id": "c5", "text": "还有人吗，讲得很实用"}
    ]
    return sample_comments
# ======================================

def fake_analysis_job(task_id, aweme_id):
    """模拟耗时分析任务：抓取(可替换)->分析(模拟)->写回结果"""
    try:
        TASKS[task_id]['status'] = 'running'
        TASKS[task_id]['progress'] = 5

        # 抓评论（可替换为真实实现）
        time.sleep(0.8)  # 模拟网络耗时
        TASKS[task_id]['progress'] = 30
        sample_comments = fetch_comments(aweme_id)

        TASKS[task_id]['progress'] = 60
        time.sleep(0.5)

        # 简单规则分析（MVP）
        positive = sum(1 for c in sample_comments if any(w in c['text'] for w in ['喜欢','支持','太美','好看','实用','推荐','超好']))
        negative = sum(1 for c in sample_comments if any(w in c['text'] for w in ['不太','差','不过']))
        total = len(sample_comments) if len(sample_comments) > 0 else 1
        neutral = total - positive - negative
        if neutral < 0:  # 防御
            neutral = 0

        # “女粉线索评分”（非常简化）
        female_cues = sum(1 for c in sample_comments if any(w in c['text'] for w in ['小姐姐','女生','女孩子']))
        female_score = round((female_cues / (len(sample_comments) or 1)), 2)

        # 关键词（简单频率）
        words = {}
        for c in sample_comments:
            for w in ['妆容','裙子','支持','喜欢','声音','穿搭','实用','推荐']:
                if w in c['text']:
                    words[w] = words.get(w, 0) + 1
        top_keywords = sorted(words.items(), key=lambda x: x[1], reverse=True)[:10]

        time.sleep(0.4)
        TASKS[task_id]['progress'] = 95

        # 结果
        result = {
            "task_id": task_id,
            "aweme_id": aweme_id,
            "summary": {
                "emotion": {
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                    "positive_pct": round(positive / (len(sample_comments) or 1), 2)
                },
                "female_signal": {
                    "score": female_score,
                    "reason": f"在 {len(sample_comments)} 条样本中检测到 {female_cues} 条含女性线索词"
                },
                "top_keywords": [k for k,_ in top_keywords],
                "recommendations": [
                    {"title": "展示妆容过程短镜头", "how_to": "30s 内切换妆前/妆后，文案加“小姐姐必看”"},
                    {"title": "穿搭展示", "how_to": "多用试穿镜头，并标注产品链接"},
                    {"title": "互动话题", "how_to": "发起‘你最喜欢的颜色’互动，引导女粉留言"}
                ]
            },
            "sample_comments": sample_comments,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }

        TASKS[task_id]['result'] = result
        TASKS[task_id]['status'] = 'done'
        TASKS[task_id]['progress'] = 100

    except Exception as e:
        # 兜底：出现异常时标记失败，前端会在 status 里看到 failed
        TASKS[task_id]['status'] = 'failed'
        TASKS[task_id]['progress'] = 100
        TASKS[task_id]['result'] = {"error": "internal_error", "detail": str(e)}

# API: 提交分析任务 -> 返回 task_id
@app.route('/api/analyze-video', methods=['POST'])
def analyze_video():
    body = request.get_json(force=True, silent=True) or {}
    aweme_id = body.get('aweme_id') or body.get('url')
    if not aweme_id:
        return jsonify({"error": "missing aweme_id or url"}), 400

    task_id = 't-' + uuid.uuid4().hex[:12]
    TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "result": None,
        "created_at": time.time()
    }

    # 异步启动分析线程（生产请用任务队列/worker）
    thread = threading.Thread(target=fake_analysis_job, args=(task_id, aweme_id), daemon=True)
    thread.start()

    return jsonify({"task_id": task_id, "status": "queued"}), 202

# API: 查询状态
@app.route('/api/analyze-status', methods=['GET'])
def analyze_status():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in TASKS:
        return jsonify({"error": "unknown task_id"}), 404
    t = TASKS[task_id]
    return jsonify({
        "task_id": task_id,
        "status": t.get('status', 'unknown'),
        "progress": t.get('progress', 0)
    })

# API: 获取最终结果
@app.route('/api/analyze-result', methods=['GET'])
def analyze_result():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in TASKS:
        return jsonify({"error": "unknown task_id"}), 404
    t = TASKS[task_id]
    if t.get('status') != 'done':
        return jsonify({"error": "not ready", "status": t.get('status')}), 409
    return jsonify(t['result'])

# 简单 health
@app.route('/_health', methods=['GET'])
def health():
    return jsonify({"ok": True, "tasks_in_memory": len(TASKS)})

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))  # 云上会注入 PORT，本地没有就用5000
    print(f"Running dev Flask server on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)