import {useState} from 'react';
import axios from 'axios';
import config from '../utils/config';
import { toast } from 'react-toastify';
import { getToken, clearToken, isTokenRejection } from '../utils/authToken';

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
            console.log(`[API] ${method} ${gUrl} ->`, response?.status, response?.data);
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
                    console.log(`[API] ${method} ${gUrl} (retried anonymously) ->`, response?.status);
                    setLoading(false);
                    return response;
                }catch(retryErr){
                    err=retryErr;
                }
            }
            console.log(`[API ERROR] ${method} ${gUrl} ->`, err.message);
            console.log('[API ERROR details]:', err.response?.data || err.request);
            if(!silent){
                if(err.response?.data?.message){
                    toast.error(err.response.data.message);
                } else if (err.response?.data?.errors) {
                    toast.error(JSON.stringify(err.response.data.errors));
                } else if (!err.response) {
                    toast.error("Network error - is the backend running?");
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