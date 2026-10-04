# Roop Studio (MVP)
Record a video, pick a different human-sounding voice and a real person's photo, get a labeled "AI-generated" video.

Pipeline: video -> faster-whisper (transcript) -> Piper (chosen voice) -> FFmpeg (compose + AI label).
Optional GPU lip-sync: set env LIPSYNC_CMD to a Wav2Lip / LivePortrait / SadTalker command using {face} {audio} {out}.

Run locally: `docker build -t roop . && docker run -p 8000:8000 roop`  -> http://localhost:8000
Demo login: demo@roop.test / Demo@12345 (change with DEMO_EMAIL, DEMO_PASSWORD)

Deploy (any Docker host, needs https for phone camera):
- Render: New Web Service -> connect repo -> Runtime: Docker. Set WHISPER_MODEL=base.
- Railway: New Project -> Deploy from repo (Dockerfile detected).
- Hugging Face Spaces: New Space -> SDK: Docker -> upload files, set PORT=7860.
First request downloads the speech and voice models, so it is slow once.
Only use your own or licensed faces and voices.
