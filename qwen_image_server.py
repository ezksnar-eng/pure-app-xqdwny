#!/usr/bin/env python3
"""
سيرفر Qwen-Image المحلي لتطبيق جيرون.
مبني على أمثلة مستودع Qwen-Image الرسمي (diffusers):
  - توليد صور:  QwenImagePipeline            (Qwen/Qwen-Image-2512)
  - تعديل صور:  QwenImageEditPlusPipeline    (Qwen/Qwen-Image-Edit-2511)

التثبيت (مرة وحدة، يحتاج نت):
  pip install torch transformers accelerate pillow
  pip install git+https://github.com/huggingface/diffusers

التشغيل:
  python qwen_image_server.py
أول تشغيل يحمّل الأوزان من Hugging Face وتنحفظ بالجهاز (كاش)، وبعدها يشتغل بدون نت.

متغيرات اختيارية:
  PORT=8000  HOST=127.0.0.1
  QWEN_IMAGE_MODEL=Qwen/Qwen-Image-2512
  QWEN_EDIT_MODEL=Qwen/Qwen-Image-Edit-2511
  OFFLOAD=1        تقليل استهلاك VRAM (أبطأ)
  HF_HUB_OFFLINE=1 منع أي اتصال بالنت (بعد ما تتحمل الأوزان)
"""
import base64, io, json, os, random, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from PIL import Image

GEN_MODEL = os.environ.get("QWEN_IMAGE_MODEL", "Qwen/Qwen-Image-2512")
EDIT_MODEL = os.environ.get("QWEN_EDIT_MODEL", "Qwen/Qwen-Image-Edit-2511")
OFFLOAD = os.environ.get("OFFLOAD", "") == "1"

if torch.cuda.is_available():
    DEVICE, DTYPE = "cuda", torch.bfloat16
elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
    DEVICE, DTYPE = "mps", torch.bfloat16
else:
    DEVICE, DTYPE = "cpu", torch.float32

LOCK = threading.Lock()  # طلب واحد كل مرة على الكرت
PIPES = {}


def get_pipe(kind):
    if kind in PIPES:
        return PIPES[kind]
    if kind == "gen":
        from diffusers import QwenImagePipeline
        pipe = QwenImagePipeline.from_pretrained(GEN_MODEL, torch_dtype=DTYPE)
    else:
        from diffusers import QwenImageEditPlusPipeline
        pipe = QwenImageEditPlusPipeline.from_pretrained(EDIT_MODEL, torch_dtype=DTYPE)
    if OFFLOAD and DEVICE == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(DEVICE)
    pipe.set_progress_bar_config(disable=None)
    PIPES[kind] = pipe
    return pipe


def snap(v):
    return max(256, int(round(int(v) / 16.0)) * 16)


def parse_size(s):
    m = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", str(s or ""))
    return (snap(m.group(1)), snap(m.group(2))) if m else (1328, 1328)


def data_url_to_image(u):
    b64 = u.split(",", 1)[1] if u.startswith("data:") else u
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generator(seed):
    seed = random.randint(0, 2**31 - 1) if seed in (None, "", -1) else int(seed)
    return torch.Generator(device="cpu" if DEVICE == "mps" else DEVICE).manual_seed(seed)


def do_generate(b):
    w, h = parse_size(b.get("size"))
    with LOCK:
        pipe = get_pipe("gen")
        with torch.inference_mode():
            out = pipe(
                prompt=b.get("prompt", ""),
                negative_prompt=b.get("negative_prompt") or " ",
                width=w, height=h,
                num_inference_steps=int(b.get("num_inference_steps") or 50),
                true_cfg_scale=float(b.get("true_cfg_scale") or 4.0),
                generator=generator(b.get("seed")),
            )
    return {"data": [{"b64_json": to_b64(out.images[0])}]}


def do_edit(b):
    imgs = [data_url_to_image(x) for x in (b.get("image") or [])]
    if not imgs:
        raise ValueError("no image")
    with LOCK:
        pipe = get_pipe("edit")
        with torch.inference_mode():
            out = pipe(
                image=imgs,
                prompt=b.get("prompt", ""),
                negative_prompt=b.get("negative_prompt") or " ",
                num_inference_steps=int(b.get("num_inference_steps") or 40),
                true_cfg_scale=float(b.get("true_cfg_scale") or 4.0),
                guidance_scale=1.0,
                num_images_per_prompt=1,
                generator=generator(b.get("seed")),
            )
    return {"data": [{"b64_json": to_b64(out.images[0])}]}


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            self._json(200, {"data": [{"id": GEN_MODEL}, {"id": EDIT_MODEL}]})
        else:
            self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path.startswith("/v1/images/generations"):
                self._json(200, do_generate(body))
            elif self.path.startswith("/v1/images/edits"):
                self._json(200, do_edit(body))
            else:
                self._json(404, {"error": {"message": "not found"}})
        except Exception as e:
            print("error:", repr(e))
            self._json(500, {"error": {"message": str(e)[:300]}})

    def log_message(self, fmt, *a):
        print("%s - %s" % (self.address_string(), fmt % a))


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"device={DEVICE} dtype={DTYPE}  gen={GEN_MODEL}  edit={EDIT_MODEL}")
    print(f"listening on http://{host}:{port}  (الأوزان تتحمل عند أول طلب)")
    ThreadingHTTPServer((host, port), H).serve_forever()
