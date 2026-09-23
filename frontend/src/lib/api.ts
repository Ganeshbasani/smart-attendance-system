const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export function token(){ return localStorage.getItem('attendx_token') || '' }
export function authHeaders(extra: Record<string,string> = {}){ return {...extra, ...(token()?{'Authorization':`Bearer ${token()}`}:{})} }
export async function api<T>(path:string, init:RequestInit={}) : Promise<T> {
  const headers = authHeaders({'Content-Type':'application/json', ...(init.headers as Record<string,string>|undefined)})
  const res = await fetch(`${API}${path}`, {...init, headers})
  if(!res.ok){
    const body = await res.json().catch(()=>({detail:'Request failed'}));
    throw new Error(body.detail || 'Request failed')
  }
  return res.json()
}
export async function login(username:string,password:string){ return api<{access_token:string}>('/auth/login',{method:'POST',body:JSON.stringify({username,password})}) }

export async function uploadDocument(file: File){
  const form=new FormData();form.append('file',file);
  const res=await fetch(`${API}/documents`,{method:'POST',headers:token()?{'Authorization':`Bearer ${token()}`}:{},body:form});
  if(!res.ok){const body=await res.json().catch(()=>({detail:'Upload failed'}));throw new Error(body.detail||'Upload failed')}
  return res.json() as Promise<{document_name:string;stored_as:string}>
}
