import React from "react";
import RegistrationPage from "../components/Registration";
import '../styles/addUserModal.css';
function AddUserModal({ onClose, reloadUserList, selectedUser }) {

    return (
        <div className="modal fade show d-block custom-modal" tabIndex="-1" role="dialog" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
            <div className="modal-dialog modal-dialog-centered" role="document">
                <div className="modal-content">
                    <div className="modal-header custom-modal-header">
                        <h5 className="modal-title w-100 text-center text-white m-0">  {selectedUser && selectedUser.id ? "Update User" : "Register User"}   </h5>
                        <button
                            type="button"
                            className="custom-close-btn"
                            aria-label="Close"
                            onClick={onClose}
                        >
                            <span className="close-icon">&times;</span>
                        </button>

                    </div>

                    <div className="modal-body">
                        <RegistrationPage isModal onClose={onClose} reloadUserList={reloadUserList} selectedUser={selectedUser} />
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AddUserModal;