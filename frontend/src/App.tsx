import {useEffect,useState} from 'react';import type {ReactNode} from 'react'
import {Routes,Route,Navigate,useLocation,useNavigate} from 'react-router-dom'
import {api,login,token} from './lib/api'
import Shell from './components/Shell'
import Login from './pages/Login'
import Student from './pages/Student'
import Faculty from './pages/Faculty'
import HOD from './pages/HOD'
import Admin from './pages/Admin'

export type User={id:number;username:string;full_name:string;role:'student'|'faculty'|'hod'|'admin';student_id?:string;department?:string;section?:string}
function Guard({children,role}:{children:ReactNode;role?:User['role']}){const raw=localStorage.getItem('attendx_user');const u=raw?JSON.parse(raw) as User:null;if(!token()||!u)return <Navigate to="/login" replace/>;if(role&&u.role!==role)return <Navigate to="/" replace/>;return <>{children}</>}
export default function App(){
 const [user,setUser]=useState<User|null>(()=>{const r=localStorage.getItem('attendx_user');return r?JSON.parse(r):null});
 const navigate=useNavigate(); const location=useLocation();
 useEffect(()=>{if(location.pathname==='/login')return;if(!user){navigate('/login')}},[user,location.pathname])
 if(location.pathname==='/login') return <Routes><Route path="/login" element={<Login onAuth={setUser}/>} /><Route path="*" element={<Navigate to="/login" replace/>}/></Routes>
 const logout=()=>{localStorage.removeItem('attendx_token');localStorage.removeItem('attendx_user');setUser(null);navigate('/login')}
 return <Shell user={user!} onLogout={logout}><Routes>
   <Route path="/" element={<Navigate to={`/${user!.role}`} replace/>}/>
   <Route path="/student" element={<Guard role="student"><Student user={user!}/></Guard>}/>
   <Route path="/faculty" element={<Guard role="faculty"><Faculty user={user!}/></Guard>}/>
   <Route path="/hod" element={<Guard role="hod"><HOD user={user!}/></Guard>}/>
   <Route path="/admin" element={<Guard role="admin"><Admin user={user!}/></Guard>}/>
   <Route path="*" element={<Navigate to="/" replace/>}/>
 </Routes></Shell>
}
export async function authenticate(username:string,password:string){const r=await login(username,password);localStorage.setItem('attendx_token',r.access_token);const me=await api<User>('/me');localStorage.setItem('attendx_user',JSON.stringify(me));return me}
