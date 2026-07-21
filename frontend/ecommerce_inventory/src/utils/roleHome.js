// Where a freshly authenticated user of each role belongs. Roles are plain
// strings on accounts.User.role and travel in the JWT's `role` claim.
//
// Without this, Auth.js sent every role to /admin/home — which renders no
// modules for a Rider, so riders saw an empty dashboard and never reached
// /rider at all.
const ROLE_HOME = {
    Rider: "/rider",
    Restaurant: "/vendor/orders",
};

const roleHome = (role) => ROLE_HOME[role] || "/admin/home";

export default roleHome;
