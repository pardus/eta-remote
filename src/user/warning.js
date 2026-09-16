const warningContainer = document.createElement('div');
warningContainer.id = 'warning-container';
document.getElementById('capture').appendChild(warningContainer);

function warning(message, can_close){
    const dialog = document.createElement('div');
    dialog.className = 'warning';

    if(can_close){
        const closeBtn = document.createElement('button');
        closeBtn.className = 'close';
        closeBtn.textContent = '✕';

        closeBtn.addEventListener('click', () => {
            dialog.remove();
        });

        dialog.appendChild(closeBtn);
    }

    const textNode = document.createTextNode(message);
    dialog.appendChild(textNode);

    warningContainer.appendChild(dialog);
}

const status = document.createTextNode("");
const status_div = document.createElement('div');
status_div.className = 'status center';
status_div.appendChild(status);
document.getElementById("capture").appendChild(status_div);

function setStatus(message){
    status.textContent = message;
    if (message.length > 0){
        status_div.style.display = 'block';
    } else {
        status_div.style.display = 'none';
    }
}
