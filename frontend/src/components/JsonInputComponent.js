import {useFormContext} from 'react-hook-form';
import { Box,Divider,Icon,TextField } from "@mui/material";
import { Delete } from '@mui/icons-material';
import { useEffect, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import { Button, IconButton } from '@mui/material';

const JsonInputComponent =({fields})=>{
    const {register} = useFormContext();
    const [keyValuePairs,setKeyValuePairs]=useState([]);
    const handleKeyValueRemove=(index)=>{
        const newPairs=keyValuePairs.filter((_,i)=>i!==index);
        setKeyValuePairs(newPairs);
    }

    useEffect(()=>{
        const def = fields.default;
        if (Array.isArray(def) && def.length > 0) {
            // Array of {key,value} objects or primitives
            setKeyValuePairs(def.map(item =>
                (item && typeof item === 'object') ? item : { key: String(item), value: '' }
            ));
        } else if (def && typeof def === 'object' && !Array.isArray(def) && Object.keys(def).length > 0) {
            // Plain object (e.g. specifications: {}) → convert to [{key,value}] pairs
            setKeyValuePairs(Object.entries(def).map(([k, v]) => ({ key: k, value: String(v) })));
        } else {
            setKeyValuePairs([{ key: '', value: '' }]);
        }
    },[])

    const handleKeyValueAdd=()=>{
        setKeyValuePairs([...keyValuePairs,{key:'',value:''}])
    }
    return(
        <Box mb={2}>
            <label>{fields.label}</label>
            <Divider sx={{marginBottom:'15px',marginTop:'10px'}}/>
            {
                keyValuePairs.map((pair,index)=>(
                    <Box key={index} display="flex" alignItems="center" mb={2}>
                        <TextField
                        fullWidth
                        margin="normal"
                        sx={{ml:1,mr:1}}
                        key={fields.name}
                        label="Key"
                        {...register(`${fields.name}[${index}].key`)}
                        defaultValue={pair.key}
                        placeholder="Key"
                        />
                        <TextField
                        fullWidth
                        margin="normal"
                        sx={{ml:1,mr:1}}
                        key={fields.name}
                        label="Value"
                        {...register(`${fields.name}[${index}].value`)}
                        defaultValue={pair.value}
                        placeholder="Value"
                        />
                        <IconButton   onClick={()=>handleKeyValueRemove(index)} variant={"outlined"} color={"secondary"}>
                            <Delete/>
                        </IconButton>
                    </Box>
                ))
            }
            <Button variant={"outlined"} color={"primary"} onClick={handleKeyValueAdd}><AddIcon/> Add</Button>
            <Divider sx={{marginBottom:'10px',marginTop:'10px'}}/>
        </Box>

    )
}
export default JsonInputComponent;