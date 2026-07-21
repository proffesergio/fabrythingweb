import {useState} from 'react';
import axios from 'axios';
import config from '../utils/config';
import { toast } from 'react-toastify';

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
        header['Authorization']=localStorage.getItem('token')?`Bearer ${localStorage.getItem('token')}`:"";
        try{
            response=await axios.request({params:params,url:gUrl,method:method,data:body,headers:header});
            console.log(`[API] ${method} ${gUrl} ->`, response?.status, response?.data);
        }
        catch(err){
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