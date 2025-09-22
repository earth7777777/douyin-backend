# app.py
# 简易后端：Flask + 内存任务队列（用于本地调试 / 前端联调）
# 运行：pip install flask flask-cors
# 然后 python app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading, time, uuid, random

app = Flask(__name__)
CORS(app)  # 开发时允许跨域，生产请加安全限制

# 内存任务存储（MVP 用）
TASKS = {}  # task_id -> {status, progress, result, created_at}

def fake_analysis_job(task_id, aweme_id):
    """模拟耗时分析任务：抓取(模拟)->分析(模拟)->写回结果"""
    TASKS[task_id]['status'] = 'running'
    TASKS[task_id]['progress'] = 5
    # 模拟“抓取评论”耗时
    time.sleep(1.2)
    TASKS[task_id]['progress'] = 30

    # 模拟从抖音抓到的一些评论样本（实际应由企业API返回）
    sample_comments = [
        {"id": "c1", "text": "小姐姐这个妆容太美了！"},
        {"id": "c2", "text": "我觉得不太行，声音太小。"},
        {"id": "c3", "text": "超喜欢！支持一下～"},
        {"id": "c4", "text": "穿搭太好看了，哪里买的裙子？"},
        {"id": "c5", "text": "还有人吗，讲得很实用"}
    ]
    TASKS[task_id]['progress'] = 60
    time.sleep(0.8)

    # 模拟情感/关键词统计（MVP：简单规则）
    positive = sum(1 for c in sample_comments if any(w in c['text'] for w in ['喜欢','支持','太美','好看','实用','推荐','超好']))
    negative = sum(1 for c in sample_comments if any(w in c['text'] for w in ['不太','差','不过']))
    neutral = len(sample_comments) - positive - negative

    # 模拟“女粉线索评分”（非常简化：出现“小姐姐/女生”等词则加分）
    female_cues = sum(1 for c in sample_comments if any(w in c['text'] for w in ['小姐姐','女生','女孩子']))
    female_score = round((female_cues / max(1, len(sample_comments))), 2)

    # 模拟关键词（简单频率）
    words = {}
    for c in sample_comments:
        for w in ['妆容','裙子','支持','喜欢','声音','穿搭','实用','推荐']:
            if w in c['text']:
                words[w] = words.get(w, 0) + 1
    top_keywords = sorted(words.items(), key=lambda x: x[1], reverse=True)[:10]
    top_keywords_str = ','.join([f"{k}({v})" for k,v in top_keywords]) if top_keywords else ''

    # 模拟耗时处理
    time.sleep(0.6)
    TASKS[task_id]['progress'] = 95

    # 最终结果结构（与前端示例对齐）
    result = {
        "task_id": task_id,
        "aweme_id": aweme_id,
        "summary": {
            "emotion": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
                "positive_pct": round(positive / len(sample_comments), 2)
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

# API: 提交分析任务 -> 返回 task_id
@app.route('/api/analyze-video', methods=['POST'])
def analyze_video():
    body = request.get_json(force=True)
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
        "status": t['status'],
        "progress": t.get('progress', 0)
    })

# API: 获取最终结果
@app.route('/api/analyze-result', methods=['GET'])
def analyze_result():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in TASKS:
        return jsonify({"error": "unknown task_id"}), 404
    t = TASKS[task_id]
    if t['status'] != 'done':
        return jsonify({"error": "not ready", "status": t['status']}), 409
    return jsonify(t['result'])

# 简单 health
@app.route('/_health', methods=['GET'])
def health():
    return jsonify({"ok": True, "tasks_in_memory": len(TASKS)})

if __name__ == '__main__':
    print("Running dev Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
