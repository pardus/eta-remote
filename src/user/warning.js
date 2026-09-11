function warning(message, can_close){
    const dialog = document.createElement('div'); 
    dialog.style.position = 'fixed'; 
    dialog.style.top = '0px';
    dialog.style.right = '0px';
    dialog.style.width = '100%';
    dialog.style.padding = '15px';

    dialog.style.backgroundColor = '#ff000057';
    dialog.style.color = '#ffffff';
    dialog.style.zIndex = '9999'; 

    if(can_close){
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.background = 'none';
        closeBtn.style.border = 'none';
        closeBtn.style.color = '#ffffff';
        closeBtn.style.padding = '8px';
        closeBtn.style.marginRight = '10px';

        closeBtn.addEventListener('click', () => {
            dialog.remove();
        });

        dialog.appendChild(closeBtn);
    }

    const textNode = document.createTextNode(message);
    dialog.appendChild(textNode);

    document.getElementById("capture").appendChild(dialog);
}

const status = document.createTextNode("");
const status_div = document.createElement('div');
status_div.style.color = '#ffffff';
status_div.style.backgroundColor = '#000000A0';
status_div.style.borderRadius = '10px';
status_div.style.padding = '10px';
status_div.style.font = '32px monospace';
status_div.classList.add('center');
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
