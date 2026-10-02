const KEY="brain_cloud_api_url";
const $=id=>document.getElementById(id);
let api=(localStorage.getItem(KEY)||"").replace(/\/$/,"");
const endpoints={
 state:["/api/state","/health"],
 tasks:["/api/tasks"],
 agents:["/api/agents","/api/agent/status"],
 audit:["/api/audit","/api/events"],
 chat:["/api/chat"]
};
function setConn(ok,label){$("connection").textContent=label|| (ok?"متصل":"غير متصل");$("connection").className="status "+(ok?"ok":"bad")}
async function request(path,opt={}){if(!api)throw new Error("API_URL_NOT_CONFIGURED");const r=await fetch(api+path,{...opt,headers:{"Accept":"application/json",...(opt.headers||{})}});const text=await r.text();let data;try{data=JSON.parse(text)}catch{data={raw:text}};if(!r.ok)throw new Error(data.error||("HTTP "+r.status));return data}
async function first(paths){let last;for(const p of paths){try{return await request(p)}catch(e){last=e}}throw last||new Error("NO_ENDPOINT")}
function setView(id){document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id===id));document.querySelectorAll("nav button").forEach(b=>b.classList.toggle("active",b.dataset.view===id));const b=document.querySelector('nav button[data-view="'+id+'"]');$("title").textContent=b?b.textContent:"Brain Cloud"}
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>setView(b.dataset.view));
function renderList(el,data,label="item"){const arr=Array.isArray(data)?data:(data?.items||data?.tasks||data?.agents||data?.events||[]);el.innerHTML=arr.length?arr.slice(0,100).map(x=>'<div class="item"><b>'+esc(x.name||x.title||x.task_id||x.id||label)+'</b><span class="badge">'+esc(x.status||x.state||x.risk||"INFO")+'</span></div>').join(""):'<div class="empty">لا توجد بيانات متاحة.</div>'}
async function refresh(){if(!api){setConn(false,"API غير مضبوط");$("overview").textContent="افتح الإعدادات وأدخل عنوان Brain API.";return}
try{const s=await first(endpoints.state);setConn(true,"متصل");$("state").textContent=s.status||s.state||s.service||"READY";$("stateDetail").textContent=s.mode||"Cloud API";$("overview").textContent=JSON.stringify(s,null,2);$("evidence").textContent=s.evidence?.status||s.evidence_status||"GATED";try{$("taskCount").textContent=(await first(endpoints.tasks)).length??"—"}catch{$("taskCount").textContent="—"}try{$("agentCount").textContent=((await first(endpoints.agents)).agents||await first(endpoints.agents)).length??"—"}catch{$("agentCount").textContent="—"}$("guards").innerHTML=["No secrets in browser","External actions require authorization","Evidence required for success","Fail closed on missing API"].map(x=>'<div class="item"><span>'+x+'</span><span class="ok">✓</span></div>').join("")}catch(e){setConn(false,"API غير متاح");$("overview").textContent="فشل الاتصال: "+e.message}}
async function loadTasks(){try{renderList($("tasksList"),await first(endpoints.tasks),"task")}catch(e){$("tasksList").innerHTML='<div class="empty">'+esc(e.message)+'</div>'}}
async function loadAgents(){try{renderList($("agentsList"),await first(endpoints.agents),"agent")}catch(e){$("agentsList").innerHTML='<div class="empty">'+esc(e.message)+'</div>'}}
async function loadAudit(){try{$("auditRaw").textContent=JSON.stringify(await first(endpoints.audit),null,2)}catch(e){$("auditRaw").textContent=e.message}}
async function loadHealth(){try{const d=await first(["/health","/api/state"]);$("healthRaw").textContent=JSON.stringify(d,null,2);$("healthGrid").innerHTML=["Runtime","Memory","Supervisor","Evidence","Recovery"].map((x,i)=>'<div class="health"><span>'+x+'</span><b>'+(i===0?(d.status||"READY"):"—")+'</b></div>').join("")}catch(e){$("healthRaw").textContent=e.message}}
$("refreshBtn").onclick=refresh;$("loadTasks").onclick=loadTasks;$("loadAgents").onclick=loadAgents;$("loadAudit").onclick=loadAudit;
$("send").onclick=async()=>{const q=$("prompt").value.trim();if(!q)return;const box=$("messages");box.innerHTML+='<div class="bubble user">'+esc(q)+'</div>';$("prompt").value="";try{const d=await request("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:q})});box.innerHTML+='<div class="bubble brain">'+esc(d.reply||d.message||JSON.stringify(d))+'</div>'}catch(e){box.innerHTML+='<div class="bubble error">'+esc(e.message)+'</div>'}};
$("saveApi").onclick=()=>{api=$("apiUrl").value.trim().replace(/\/$/,"");if(api)localStorage.setItem(KEY,api);refresh()};
$("clearApi").onclick=()=>{localStorage.removeItem(KEY);api="";refresh()};
$("apiUrl").value=api;
function esc(v){return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]))}
refresh();setInterval(refresh,15000);
setView("dashboard");

const customerEndpoints=["/api/customers","/api/customer/requests"];
async function submitCustomerRequest(e){
 e.preventDefault();
 const result=$("customerResult"), status=$("customerStatus");
 const payload={display_name:$("customerName").value.trim(),service:$("customerService").value.trim(),need:$("customerNeed").value.trim(),marketing_consent:$("customerMarketing").checked};
 result.textContent="جارٍ إرسال الطلب إلى Brain API…";
 try{
   const d=await first(customerEndpoints.map(p=>p));
   result.textContent=JSON.stringify(d,null,2);
 }catch(err){
   result.textContent="لم يتم إنشاء طلب فعلي: "+err.message+" — لا توجد بيانات محلية بديلة.";
   status.innerHTML='<div class="item"><b>REQUEST</b><span class="badge">API REQUIRED</span></div><div class="item"><b>MARKETING CONSENT</b><span class="badge">'+(payload.marketing_consent?"GRANTED":"NOT GRANTED")+'</span></div>';
 }
}
if($("customerRequest")) $("customerRequest").onsubmit=submitCustomerRequest;
