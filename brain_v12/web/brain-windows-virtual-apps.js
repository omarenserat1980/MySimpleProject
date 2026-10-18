(function(){
'use strict';
const $=id=>document.getElementById(id);
const files={
 'README.txt':'Brain Windows Desktop Simulator\nهذه مساحة افتراضية وليست نظام Windows فعليًا.',
 'notes.txt':'اكتب ملاحظاتك هنا ثم اضغط حفظ.',
 'system-info.txt':'Environment: SIMULATED\nOS kernel: none\nEXE support: unavailable'
};
const STORAGE_KEY='brain-windows-simulator-files-v1';
try{const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');if(saved&&typeof saved==='object'&&!Array.isArray(saved)){Object.keys(saved).forEach(k=>{if(typeof saved[k]==='string'&&k.length<=120)files[k]=saved[k]})}}catch(_e){}
function persistFiles(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(files));return true}catch(_e){note('تعذر التخزين المحلي؛ صدّر الملفات للاحتفاظ بنسخة.');return false}}
let selected='README.txt';
function note(s){const n=$('notice');if(!n)return;n.textContent=s;n.classList.add('show');setTimeout(()=>n.classList.remove('show'),2500)}
function addWindow(id,title,body){if($(id))return;const w=document.createElement('section');w.className='window';w.id=id;w.innerHTML='<header class="titlebar"><span>'+title+'</span><div class="wincontrols"><button data-min>—</button><button data-close>✕</button></div></header><div class="winbody">'+body+'</div>';document.querySelector('.desktop').appendChild(w);w.querySelector('[data-min]').onclick=()=>w.classList.remove('open');w.querySelector('[data-close]').onclick=()=>w.classList.remove('open')}
function open(id){document.querySelectorAll('.window').forEach(w=>w.classList.remove('open'));$(id).classList.add('open');$('start')?.classList.remove('open')}
function render(){const g=$('virtual-grid');if(!g)return;g.replaceChildren();Object.keys(files).sort().forEach(name=>{const b=document.createElement('button');b.className='file';b.innerHTML='<b>📄</b>';const t=document.createElement('span');t.textContent=name;b.appendChild(t);b.onclick=()=>select(name);g.appendChild(b)});$('virtual-status').textContent=Object.keys(files).length+' ملفات افتراضية محفوظة في ذاكرة الصفحة.'}
function select(name){selected=name;$('virtual-name').value=name;$('virtual-content').value=files[name]||''}
function install(){
 const fw=$('files');if(fw){const body=fw.querySelector('.winbody');body.innerHTML='<div class="toolbar"><button id="vf-new">＋ ملف جديد</button><button id="vf-export">تصدير الكل</button><button id="vf-refresh">تحديث</button></div><h3>مساحة الملفات الافتراضية C:\\Brain</h3><div class="filegrid" id="virtual-grid"></div><h3>محرر النصوص</h3><input id="virtual-name" placeholder="اسم الملف" style="width:100%;padding:9px;margin:8px 0;border:1px solid #cbd5e1;border-radius:5px"><textarea id="virtual-content" class="editor" style="width:100%;min-height:150px;padding:10px"></textarea><div class="toolbar" style="margin-top:8px"><button id="vf-save">حفظ</button><button id="vf-delete">حذف</button></div><div id="virtual-status" class="status"></div>';
 const style=document.createElement('style');style.textContent='.editor{font:13px ui-monospace,monospace;border:1px solid #cbd5e1;border-radius:5px}#virtual-grid .file{background:transparent;border:0;color:#17202b}';document.head.appendChild(style);
 $('vf-new').onclick=()=>{const name='new-'+(Object.keys(files).length+1)+'.txt';files[name]='';select(name);render();note('أُنشئ ملف افتراضي؛ اضغط حفظ.')};
 $('vf-save').onclick=()=>{const name=$('virtual-name').value.trim();if(!name||/[\/\\\\]/.test(name)){note('اكتب اسم ملف صالحًا دون مسارات.');return}files[name]=$('virtual-content').value;selected=name;persistFiles();render();note('حُفظ في التخزين المحلي لهذا المتصفح.')};
 $('vf-delete').onclick=()=>{const name=$('virtual-name').value.trim();if(!(name in files)){note('الملف غير موجود.');return}delete files[name];persistFiles();$('virtual-name').value='';$('virtual-content').value='';render();note('حُذف من مساحة المحاكاة والتخزين المحلي.')};
 $('vf-refresh').onclick=render;
 $('vf-export').onclick=()=>{const blob=new Blob([Object.keys(files).sort().map(n=>'===== '+n+' =====\n'+files[n]).join('\n\n')],{type:'text/plain;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='brain-virtual-files.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
 render();select(selected)}
 const terminalBody='<p>Shell تجريبي: الأوامر محصورة في مساحة المحاكاة ولا تنفذ أوامر نظام الجهاز.</p><div id="virtual-shell-output" class="terminal">Brain Shell Simulator [SIMULATED]\nاكتب help لعرض الأوامر.</div><form id="virtual-shell-form" class="terminal-input"><input id="virtual-shell-input" autocomplete="off" placeholder="help"><button class="primary">تنفيذ</button></form>';
 addWindow('virtual-shell','⌨️ Brain Shell',terminalBody);
 const menu=document.querySelector('.apps');if(menu&&!menu.querySelector('[data-shell]')){const b=document.createElement('button');b.dataset.shell='1';b.innerHTML='⌨️<br>Shell';b.onclick=()=>open('virtual-shell');menu.appendChild(b)}
 const taskleft=document.querySelector('.taskleft');if(taskleft&&!taskleft.querySelector('[data-shell-open]')){const b=document.createElement('button');b.className='taskbtn';b.dataset.shellOpen='1';b.textContent='⌨️';b.title='Brain Shell';b.onclick=()=>open('virtual-shell');taskleft.appendChild(b)}
 $('virtual-shell-form').onsubmit=e=>{e.preventDefault();const inp=$('virtual-shell-input'),out=$('virtual-shell-output'),cmd=inp.value.trim(),a=cmd.split(' '),op=(a.shift()||'').toLowerCase();let result='';if(op==='help')result='help, ver, dir, type <file>, echo <text>, whoami, clear';else if(op==='ver')result='Brain Windows Desktop Simulator [SIMULATED]';else if(op==='dir')result=Object.keys(files).sort().join('\n')||'(empty)';else if(op==='type'){const n=a.join(' ');result=n in files?files[n]:'File not found: '+n}else if(op==='echo')result=a.join(' ');else if(op==='whoami')result='brain\\simulated-user';else if(op==='clear'){out.textContent='';inp.value='';return}else result='أمر غير مدعوم. لا يتم تشغيل أوامر النظام أو ملفات EXE.';out.textContent+='\nC:\\Brain> '+cmd+'\n'+result+'\n';out.scrollTop=out.scrollHeight;inp.value=''};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();