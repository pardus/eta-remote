function warning(message){
    const dialog = document.createElement('div'); 
    dialog.style.position = 'fixed'; 
    dialog.style.top = '0px';
    dialog.style.right = '0px';
    dialog.style.width = '100vw';
    dialog.style.padding = '15px';

    dialog.style.backgroundColor = '#ff0000';
    dialog.style.color = '#ffffff';
    dialog.style.zIndex = '9999'; 

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

    const textNode = document.createTextNode(message);
    dialog.appendChild(textNode);

    document.body.appendChild(dialog);
}
