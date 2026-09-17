const $=id=>document.getElementById(id);
let lastUrl=null;
const status=t=>{$('status').textContent=t};
$('image').addEventListener('change',()=>{$('imageInfo').textContent=$('image').files[0]?`تم اختيار: ${$('image').files[0].name}`:'اختر صورة واضحة للمنتج.'});
$('generate').addEventListener('click',async()=>{
 const file=$('image').files[0]; if(!file){status('اختر صورة المنتج أولاً.');return}
 if(!window.MediaRecorder){status('المتصفح لا يدعم إنشاء الفيديو. جرّب Chrome حديث.');return}
 const img=new Image(); img.src=URL.createObjectURL(file); await img.decode();
 const c=document.createElement('canvas'); c.width=720;c.height=1280;const ctx=c.getContext('2d');
 const stream=c.captureStream(30); const chunks=[]; const rec=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9'});
 rec.ondataavailable=e=>e.data.size&&chunks.push(e.data); rec.onstop=()=>{if(lastUrl)URL.revokeObjectURL(lastUrl);lastUrl=URL.createObjectURL(new Blob(chunks,{type:'video/webm'}));$('preview').src=lastUrl;$('preview').style.display='block';$('download').disabled=false;$('downloadLink').href=lastUrl;$('downloadLink').download='foras-ad.webm';$('downloadLink').hidden=false;status('✅ تم إنشاء الفيديو. اضغط حفظ الفيديو.');};
 const product=$('product').value||'المنتج';const price=$('price').value;const contact=$('contact').value;const copy=$('copy').value;
 rec.start();let start=performance.now();
 function frame(now){let t=(now-start)/1000;if(t>=8){rec.stop();return}
   ctx.fillStyle='#111827';ctx.fillRect(0,0,c.width,c.height);ctx.fillStyle='#fff';ctx.textAlign='center';ctx.font='bold 42px Arial';ctx.fillText(product,360,90);
   const scale=Math.min(560/img.width,650/img.height);const w=img.width*scale,h=img.height*scale;ctx.drawImage(img,(720-w)/2,150+(Math.sin(t*2)*8),w,h);
   ctx.fillStyle='#fff';ctx.font='28px Arial';wrapText(ctx,copy,360,880,600,42);
   if(price){ctx.font='bold 48px Arial';ctx.fillText(price,360,1040)}
   if(contact){ctx.font='bold 30px Arial';ctx.fillText('للتواصل: '+contact,360,1130)}
   ctx.font='22px Arial';ctx.fillText('Foras Ads',360,1215);requestAnimationFrame(frame)
 }
 status('⏳ جاري إنشاء فيديو 8 ثوانٍ...');requestAnimationFrame(frame);
});
$('download').addEventListener('click',()=>{$('downloadLink').click()});
function wrapText(ctx,text,x,y,maxWidth,lineHeight){const words=text.split(/\s+/);let line='';for(const word of words){const test=line?line+' '+word:word;if(ctx.measureText(test).width>maxWidth&&line){ctx.fillText(line,x,y);line=word;y+=lineHeight}else line=test}if(line)ctx.fillText(line,x,y)}
