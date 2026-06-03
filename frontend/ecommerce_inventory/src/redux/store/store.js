import { configureStore } from "@reduxjs/toolkit";
import sidebarReducer from "../reducer/sidebardata";
import IsLoggedInReducer from "../reducer/IsLoggedInReducer";
import cartReducer from "../reducer/cartSlice";

const store=configureStore({
    reducer:{
        sidebardata:sidebarReducer,
        isLoggedInReducer:IsLoggedInReducer,
        cart:cartReducer,
    }
});

export default store;