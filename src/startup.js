document.querySelector('.skip').addEventListener('click',e=>{e.preventDefault();main.focus();main.scrollIntoView()});
addEventListener('hashchange',()=>render());render(false);
