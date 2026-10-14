/** Small browser-native helpers; no runtime libraries or storage. */
export const copy=value=>structuredClone(value);
export const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;
export const assert=(condition,message)=>{if(!condition)throw new Error(message);};
export const exact=(value,keys)=>object(value)&&Object.keys(value).length===keys.length&&keys.every(key=>Object.hasOwn(value,key));
export const int=(value,min,max)=>Number.isInteger(value)&&value>=min&&value<=max;
export const finite=value=>typeof value==='number'&&Number.isFinite(value)&&Math.abs(value)<=1e12;
export function shuffled(values) {
  const output=[...values];
  const below=max=>{let value;const limit=Math.floor(4294967296/max)*max;do{value=crypto.getRandomValues(new Uint32Array(1))[0];}while(value>=limit);return value%max;};
  for(let i=output.length-1;i>0;i--){const j=below(i+1);[output[i],output[j]]=[output[j],output[i]];}
  return output;
}
export function pyFixed(value,digits=0) {
  assert(Number.isFinite(value)&&int(digits,0,8),'Invalid formatted number');
  const negative=value<0||Object.is(value,-0),buffer=new ArrayBuffer(8),view=new DataView(buffer);
  view.setFloat64(0,Math.abs(value));
  const bits=view.getBigUint64(0),rawExponent=Number((bits>>52n)&2047n);
  let mantissa=bits&((1n<<52n)-1n);
  if(rawExponent)mantissa|=1n<<52n;
  const exponent=rawExponent?rawExponent-1023-52:-1074;
  let numerator=mantissa*10n**BigInt(digits),denominator=1n;
  if(exponent>=0)numerator<<=BigInt(exponent);else denominator<<=BigInt(-exponent);
  let rounded=numerator/denominator;
  const remainder=numerator%denominator;
  if(remainder*2n>denominator||remainder*2n===denominator&&rounded%2n===1n)rounded++;
  let text=rounded.toString().padStart(digits+1,'0');
  if(digits)text=text.slice(0,-digits)+'.'+text.slice(-digits);
  return (negative?'-':'')+text;
}
export function currency(value) {
  return (value<0?'-':'')+'$'+pyFixed(Math.abs(value),0).replace(/\B(?=(\d{3})+(?!\d))/g,',');
}
export function canonicalJSON(value) {
  if(Array.isArray(value))return '['+value.map(canonicalJSON).join(',')+']';
  if(object(value))return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+canonicalJSON(value[key])).join(',')+'}';
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
}
export function to64(bytes) {
  let text='';for(const byte of bytes)text+=String.fromCharCode(byte);
  return btoa(text).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/g,'');
}
export function from64(text,max=16000) {
  assert(typeof text==='string'&&text.length>0&&text.length<=max&&/^[A-Za-z0-9_-]+$/.test(text),'Invalid saved token');
  return Uint8Array.from(atob(text.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-text.length%4)%4)),c=>c.charCodeAt(0));
}
async function stream(bytes,transform,max) {
  const reader=new Blob([bytes]).stream().pipeThrough(transform).getReader();
  let length=0;const chunks=[];
  while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;
    if(length>max){await reader.cancel();throw new Error('Saved state too large');}chunks.push(value);}
  const result=new Uint8Array(length);let offset=0;
  for(const chunk of chunks){result.set(chunk,offset);offset+=chunk.length;}return result;
}
export async function encodeJSON(value,maxJSON=16384,maxToken=4096) {
  const bytes=new TextEncoder().encode(canonicalJSON(value));assert(bytes.length<=maxJSON,'Saved state too large');
  const token=to64(await stream(bytes,new CompressionStream('deflate'),maxToken));assert(token.length<=maxToken,'Saved token too large');return token;
}
export async function decodeJSON(token,maxJSON=16384,maxToken=4096) {
  const bytes=await stream(from64(token,maxToken),new DecompressionStream('deflate'),maxJSON);
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
export function parseNumber(raw) {
  if(typeof raw!=='string'||raw.length>64||!raw.trim())return null;
  let value=raw.trim().replace(/^\$\s*/,'');
  if(!/^[+-]?(?:(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value))return null;
  value=Number(value.replaceAll(',',''));return finite(value)?value:null;
}
export const numericText=value=>typeof value==='string'&&value.length<=64&&/^[0-9eE.,\s$+\-]*$/.test(value);
