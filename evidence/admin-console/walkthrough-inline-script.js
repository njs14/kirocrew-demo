
const dialog=document.querySelector('dialog'), zoom=document.getElementById('dialog-image'), title=document.getElementById('dialog-title');
document.querySelectorAll('.image-button').forEach(button=>button.addEventListener('click',()=>{const source=button.querySelector('img');zoom.src=source.src;zoom.alt=source.alt;title.textContent=button.closest('.step').querySelector('h2').textContent;dialog.showModal();}));
document.getElementById('close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}});
const nav=[...document.querySelectorAll('.toc a')];
const observer=new IntersectionObserver(entries=>{const visible=entries.filter(x=>x.isIntersecting);if(visible.length){nav.forEach(a=>a.removeAttribute('aria-current'));const active=nav.find(a=>a.hash==='#'+visible[0].target.id);if(active)active.setAttribute('aria-current','true');}},{rootMargin:'-10% 0px -60% 0px'});document.querySelectorAll('.step,.flow,.notes').forEach(node=>observer.observe(node));
