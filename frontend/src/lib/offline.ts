import { openDB } from 'idb'
const DB='attendx-offline'; const STORE='events'
async function db(){return openDB(DB,1,{upgrade(d){if(!d.objectStoreNames.contains(STORE))d.createObjectStore(STORE,{keyPath:'client_event_id'})}})}
export async function queueEvent(payload:unknown){const client_event_id=crypto.randomUUID();(await db()).put(STORE,{client_event_id,payload,created_at:new Date().toISOString()});return client_event_id}
export async function queued(){return (await db()).getAll(STORE)}
export async function clearEvent(id:string){(await db()).delete(STORE,id)}
