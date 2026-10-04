const $ = id => document.getElementById(id);
let video = null, photo = null, voice = null, resultUrl = null, timer = null;
const MSGS = ["Listening to your video...", "Writing down what you said...", "Recording the new voice...", "Putting your video together..."];

$("li").onclick = async () => {
  try {
    const r = await fetch("/api/voices");
    if (!r.ok) throw new Error();
    const list = await r.json();
    renderVoices(list);
    $("login").hidden = true; $("studio").hidden = false;
  } catch { show("lerr", "Could not reach the server. Please try again."); }
};

function renderVoices(list) {
  $("voices").innerHTML = "";
  list.forEach((v, i) => {
    const [name, desc] = v.label.split(" - ");
    const b = document.createElement("button");
    b.className = "voice"; b.type = "button";
    b.innerHTML = `<i>${name[0]}</i><span><b>${name}</b><small>${desc || ""}</small></span>`;
    b.onclick = () => { voice = v.id; document.querySelectorAll(".voice").forEach(x => x.classList.remove("on")); b.classList.add("on"); };
    $("voices").appendChild(b);
    if (i === 0) b.click();
  });
}

function pickVideo(e) {
  video = e.target.files[0] || null;
  $("vname").textContent = video ? video.name : "No video selected";
  $("vname").classList.toggle("ok", !!video);
}
$("vrec").onchange = pickVideo; $("vup").onchange = pickVideo;

$("pf").onchange = e => {
  photo = e.target.files[0] || null;
  if (photo) { $("pimg").src = URL.createObjectURL(photo); $("pimg").hidden = false; $("ptxt").hidden = true; }
};

function show(id, msg) { $(id).textContent = msg; $(id).hidden = !msg; }

$("go").onclick = async () => {
  show("err", "");
  if (!video) return show("err", "Please record or upload a video first.");
  if (!$("ok").checked) return show("err", "Please confirm the consent box.");
  const f = new FormData();
  f.append("email", $("em").value); f.append("password", $("pw").value);
  f.append("voice", voice); f.append("consent", true); f.append("video", video);
  if (photo) f.append("photo", photo);
  $("go").disabled = true; $("prog").hidden = false; $("result").hidden = true;
  let n = 0; $("ptext").textContent = MSGS[0];
  timer = setInterval(() => { n = Math.min(n + 1, MSGS.length - 1); $("ptext").textContent = MSGS[n]; }, 15000);
  try {
    const r = await fetch("/api/make", { method: "POST", body: f });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || "Something went wrong."); }
    if (resultUrl) URL.revokeObjectURL(resultUrl);
    resultUrl = URL.createObjectURL(await r.blob());
    $("rv").src = resultUrl; $("dl").href = resultUrl;
    $("result").hidden = false; $("result").scrollIntoView({ behavior: "smooth" });
  } catch (e) { show("err", e.message); }
  clearInterval(timer); $("prog").hidden = true; $("go").disabled = false;
};

$("again").onclick = () => { $("result").hidden = true; window.scrollTo({ top: 0, behavior: "smooth" }); };
