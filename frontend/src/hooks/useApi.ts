import {useEffect,useState} from 'react';
import {api} from '../lib/api'
export function useApi<T>(path:string, deps:any[]=[]){const [data,setData]=useState<T|null>(null);const [loading,setLoading]=useState(true);const [error,setError]=useState('');const reload=async()=>{setLoading(true);try{setData(await api<T>(path));setError('')}catch(e){setError(e instanceof Error?e.message:'Failed')}finally{setLoading(false)}};useEffect(()=>{reload()},deps);return {data,loading,error,reload}}
