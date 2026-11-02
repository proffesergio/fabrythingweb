import { configureStore } from "@reduxjs/toolkit";
import sidebarReducer from "../reducer/sidebardata";
import IsLoggedInReducer from "../reducer/IsLoggedInReducer";
import cartReducer from "../reducer/cartSlice";
import foodCartReducer from "../../food/redux/foodCartSlice";

const store=configureStore({
    reducer:{
        sidebardata:sidebarReducer,
        isLoggedInReducer:IsLoggedInReducer,
        cart:cartReducer,
        foodCart:foodCartReducer,
    }
});

export default store;