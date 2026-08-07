import {useFormContext} from 'react-hook-form';
import { Box,FormControl,InputLabel,Select,MenuItem, FormControlLabel, Switch, TextField } from "@mui/material";
import JsonInputComponent from './JsonInputComponent';
import { devLog } from '../utils/devLog';

const StepJsonComponents = ({formConfig,fieldType}) => {
    const {register} = useFormContext();
    const jsonFields=formConfig.data.json;
    devLog(jsonFields);
    return (
        <Box>
            {
                    jsonFields.map((field,index)=>(
                        <JsonInputComponent fields={field} key={field.name} />
                    ))
            }
        </Box>
    )
}
export default StepJsonComponents;