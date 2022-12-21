const show_result_area = document.getElementById("show_result_area");

for (let i = 0 ; i < 100 ; i++) {
    var rel_or_not = document.createElement('p')
    rel_or_not.classList.add('fw-bold');
    rel_or_not.classList.add('mt-2');

    var div_img = document.createElement('div');
    var img = document.createElement('img');
    var str_src = "";
    img.src = str_src;
    div_img.classList.add("col-2");
    div_img.classList.add("shadow-lg");
    div_img.classList.add("p-2");
    div_img.classList.add("mb-3");
    div_img.classList.add("mx-3");
    div_img.classList.add("bg-body");
    div_img.classList.add("rounded");
    div_img.appendChild(img);
    div_img.appendChild(rel_or_not);
    
    show_result_area.appendChild(div_img);
}