import {useState} from 'react';
import axios from 'axios';
import config from '../utils/config';
import { toast } from 'react-toastify';
import { getToken, clearToken, isTokenRejection } from '../utils/authToken';
import { devLog } from '../utils/devLog';

function useApi(){
    const [error,setError]=useState("");
    const [loading,setLoading]=useState(false);
    // Pass silent:true to suppress the error toast (for expected errors the caller
    // handles itself, e.g. a 404 that just means "ask the guest for their phone").
    // Pass rawError:true to receive the error response ({status,data}) instead of
    // null, so the caller can read DRF field errors out of the {data,message}
    // envelope. Default stays null for the existing call sites.
    const callApi=async ({url,method="GET",body={},header={},params={},silent=false,rawError=false})=>{
        let gUrl=config.API_URL+url;
        setLoading(true);
        let response=null;
        // getToken() drops an already-expired token instead of attaching it —
        // see utils/authToken.js for why a stale JWT broke *guest* checkout.
        const token=getToken();
        header['Authorization']=token?`Bearer ${token}`:"";
        try{
            response=await axios.request({params:params,url:gUrl,method:method,data:body,headers:header});
            devLog(`[API] ${method} ${gUrl} ->`, response?.status, response?.data);
        }
        catch(err){
            // The server rejected the token itself (revoked, re-signed, or from
            // an older deployment's SECRET_KEY — none of which the expiry check
            // can see). Drop it and retry once as an anonymous caller: public
            // endpoints then succeed, and authenticated ones fail the same way
            // they would for a logged-out visitor instead of failing forever.
            if(token && err.response?.status===401 && isTokenRejection(err.response?.data)){
                clearToken();
                try{
                    response=await axios.request({params:params,url:gUrl,method:method,data:body,
                                                  headers:{...header,Authorization:""}});
                    devLog(`[API] ${method} ${gUrl} (retried anonymously) ->`, response?.status);
                    setLoading(false);
                    return response;
                }catch(retryErr){
                    err=retryErr;
                }
            }
            devLog(`[API ERROR] ${method} ${gUrl} ->`, err.message);
            devLog('[API ERROR details]:', err.response?.data || err.request);
            if(!silent){
                if(err.response?.data?.message){
                    toast.error(err.response.data.message);
                } else if (err.response?.data?.errors) {
                    toast.error(JSON.stringify(err.response.data.errors));
                } else if (!err.response) {
                    // No response object at all means the request never completed:
                    // the server was asleep (Render's free plan spins down after
                    // ~15 min idle and its edge answers without CORS headers, which
                    // the browser then blocks), the connection dropped, or an
                    // extension cancelled it. The browser deliberately refuses to
                    // tell JS which — they are indistinguishable from here. So say
                    // what the customer can act on instead of accusing the backend:
                    // a cold start is by far the most common cause and it fixes
                    // itself on a retry a few seconds later.
                    toast.error("Couldn't reach the server — it may be waking up. Please retry in a few seconds.");
                }
            }
            setError(err)
            if(rawError && err.response){
                setLoading(false);
                return err.response;
            }
        }
        setLoading(false);
        return response;
    }
    return {callApi,error,loading};
}
export default useApi;