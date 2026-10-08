/* Browser companion to the simple PV model. Inputs are hypothetical. */
(function(root){
  'use strict';
  function calculate(p){
    const keys=['n','ltv','uplift','fixed','transition','exit','spend'];
    for(const k of keys){if(typeof p[k]!=='number'||!Number.isFinite(p[k])||p[k]<0)throw new Error('すべて有限の非負数で入力してください。');}
    if(p.n<=0||p.exit>1||p.spend>1)throw new Error('人数は正、比率は0〜100％にしてください。');
    const remaining=(1-p.spend)*(p.ltv+p.uplift);
    return {delta:p.n*((1-p.exit)*remaining-p.ltv)+p.fixed-p.transition,
            threshold:remaining===0?null:1-(p.ltv-(p.fixed-p.transition)/p.n)/remaining};
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={calculate};
  root.DiscModel={calculate};
  if(typeof document==='undefined')return;
  const form=document.getElementById('model-form');
  const money=new Intl.NumberFormat('ja-JP',{maximumFractionDigits:2});
  function run(){
    try{
      const p={}; for(const k of ['n','ltv','uplift','fixed','transition','exit','spend'])p[k]=Number(form.elements[k].value);
      p.fixed*=1e8;p.transition*=1e8;p.exit/=100;p.spend/=100;
      const r=calculate(p);
      document.getElementById('delta').textContent=money.format(r.delta/1e8)+' 億円';
      document.getElementById('threshold').textContent=r.threshold===null?'境界なし':money.format(r.threshold*100)+'％';
      document.getElementById('error').textContent='';
      document.getElementById('meaning').textContent=r.threshold===null?'残る人の利益がゼロなので、離脱率による境界を計算できません。':r.threshold<0?'この仮定では、追加離脱ゼロでも利益差はマイナスです。':r.threshold>1?'この仮定では、全員退出しても固定費の差だけで利益が残ります。設定を再確認してください。':'境界は予測される離脱率ではありません。ここを超えると、この入力条件で利益差がマイナスになります。';
    }catch(e){document.getElementById('error').textContent=e.message;document.getElementById('delta').textContent='—';document.getElementById('threshold').textContent='—';}
  }
  form.addEventListener('input',run);form.addEventListener('submit',e=>{e.preventDefault();run();});run();
})(typeof globalThis!=='undefined'?globalThis:this);
