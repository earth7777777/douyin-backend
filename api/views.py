# api/views.py
# 简单的同步内存任务实现，用于联调。生产环境请用真正的任务队列和存储。
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import threading, time, uuid, json

# 内存任务存储（测试用）
TASKS = {}

def fake_analysis_job(task_id, aweme_id):
    TASKS[task_id]['status'] = 'running'
    TASKS[task_id]['progress'] = 5
    time.sleep(1.2)
    TASKS[task_id]['progress'] = 30

    sample_comments = [
        {"id": "c1", "text": "小姐姐这个妆容太美了！"},
        {"id": "c2", "text": "我觉得不太行，声音太小。"},
        {"id": "c3", "text": "超喜欢！支持一下～"},
        {"id": "c4", "text": "穿搭太好看了，哪里买的裙子？"},
        {"id": "c5", "text": "还有人吗，讲得很实用"}
    ]
    TASKS[task_id]['progress'] = 60
    time.sleep(0.6)

    positive = sum(1 for c in sample_comments if any(w in c['text'] for w in ['喜欢','支持','太美','好看','实用','推荐','超好']))
    negative = sum(1 for c in sample_comments if any(w in c['text'] for w in ['不太','差','不过']))
    neutral = len(sample_comments) - positive - negative

    female_cues = sum(1 for c in sample_comments if any(w in c['text'] for w in ['小姐姐','女生','女孩子']))
    female_score = round((female_cues / max(1, len(sample_comments))), 2)

    words = {}
    for c in sample_comments:
        for w in ['妆容','裙子','支持','喜欢','声音','穿搭','实用','推荐']:
            if w in c['text']:
                words[w] = words.get(w, 0) + 1
    top_keywords = sorted(words.items(), key=lambda x: x[1], reverse=True)[:10]

    time.sleep(0.4)
    TASKS[task_id]['progress'] = 95

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

@csrf_exempt
def analyze_video(request):
    if request.method != 'POST':
        return JsonResponse({"error": "method not allowed"}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    aweme_id = body.get('aweme_id') or body.get('url')
    if not aweme_id:
        return JsonResponse({"error": "missing aweme_id or url"}, status=400)

    task_id = 't-' + uuid.uuid4().hex[:12]
    TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "result": None,
        "created_at": time.time()
    }

    thread = threading.Thread(target=fake_analysis_job, args=(task_id, aweme_id), daemon=True)
    thread.start()

    return JsonResponse({"task_id": task_id, "status": "queued"}, status=202)

def analyze_status(request):
    task_id = request.GET.get('task_id')
    if not task_id or task_id not in TASKS:
        return JsonResponse({"error": "unknown task_id"}, status=404)
    t = TASKS[task_id]
    return JsonResponse({"task_id": task_id, "status": t['status'], "progress": t.get('progress', 0)})

def analyze_result(request):
    task_id = request.GET.get('task_id')
    if not task_id or task_id not in TASKS:
        return JsonResponse({"error": "unknown task_id"}, status=404)
    t = TASKS[task_id]
    if t['status'] != 'done':
        return JsonResponse({"error": "not ready", "status": t['status']}, status=409)
    return JsonResponse(t['result'])
