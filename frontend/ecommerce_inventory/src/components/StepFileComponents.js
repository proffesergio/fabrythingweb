import { Box } from "@mui/material";
import FileInputComponent from './FileInputComponents';

const StepFileComponents = ({formConfig }) => {
    return (
        <Box>
            {formConfig?.data?.file?.map((field,index)=>(
                <FileInputComponent field={field} key={index} />
            ))}
        </Box>
    )
}
export default StepFileComponents;