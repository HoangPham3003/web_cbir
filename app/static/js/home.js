let nearest_images = null;
let show_nearest_images = null;
let query_path = null;
let query_features = null;
let n_pos = null;
let n_neg = null;
let labeled_data_set = null;
let unlabeled_data_set_indices = null;

const grid_nearest_image = document.getElementById("grid_nearest_image");
const show_result_area_children = show_result_area.children;
const spinner = document.getElementById("spinner");
const spinner_rf = document.getElementById("spinner_rf");
const runtime_header = document.getElementById("runtime_header");
const runtime_show = document.getElementById("runtime_show");



const $ = jQuery;

function loadFile(event) {
    let blob = new Blob([event.target.files[0]], { type: "image/jpeg" });
    let fname = event.target.files[0].name;
    process(blob, fname, false);
}
  
function process(blob, fname, isDrop) {
    const image = document.getElementById("showUploadImage");
    const result = document.getElementById("result");
    
    let srcBlobImg = URL.createObjectURL(blob);
    image.src = srcBlobImg;
    result.style.display = "block";
    
    runtime_header.classList.add('d-none');
    runtime_show.innerText = "";

    grid_nearest_image.classList.add("d-none");
    spinner.classList.remove("d-none");

    if (show_result_area.classList.contains("d-none") === false) {
        show_result_area.classList.add("d-none");
    }

    nearest_images = null;
    show_nearest_images = null;
    query_path = null;
    query_features = null;
    n_pos = null;
    n_neg = null;
    labeled_data_set = null;
    unlabeled_data_set_indices = null;

    const data = new FormData();
    data.append("file", blob, fname);
    $.ajax({
        url: "/",
        type: "POST",
        processData: false,
        contentType: false,
        data: data,
        success: (ret) => {
            var data = ret.data;
            
            n_pos = data['n_pos'];
            n_neg = data['n_neg'];
            labeled_data_set = data['labeled_data_set'];
            unlabeled_data_set_indices = data['unlabeled_data_set_indices'];
           
            var precision = n_pos / 100;
            var precision_area = document.getElementById("precision");
            precision_area.innerText = "" + precision;
            
            runtime = data['run_time'];
            runtime_header.classList.remove('d-none');
            runtime_show.innerText = "" + runtime;


            nearest_images = data['nearest_images'];
            show_nearest_images = data['show_nearest_images'];
            query_path = data['query_path'];
            query_features = data['query_features'];

            var arr_split = query_path.split("__");
            var temp = arr_split[0].split('/');
            var query_class = temp[temp.length-1];
            var query_name = arr_split[1] + '.jpg';
            
            var nearest_img = null;
            var img_class = null;
            var img_name = null;

            for (i = 0 ; i < 100 ; i++) {
                d = show_result_area_children[i];
                children_div = d.children;
                img = d.getElementsByTagName("img")[0];
                rel_or_not = d.getElementsByTagName("p")[0];

                if (rel_or_not.classList.contains("text-success") === true) {
                    rel_or_not.classList.remove("text-success");
                }
                if (rel_or_not.classList.contains("text-danger") === true) {
                    rel_or_not.classList.remove("text-danger");
                }

                nearest_img = show_nearest_images[i];
                img_class = nearest_img.class;
                img_name = nearest_img.name;

                if (img_class === query_class){
                    rel_or_not.classList.add('text-success');
                    rel_or_not.innerText = "RELEVANT";
                }
                else {
                    rel_or_not.classList.add('text-danger');
                    rel_or_not.innerText = "NON-RELEVANT";
                }
                
                var str_src = "static/CorelDB1K/" + img_class + "/"+img_name;
                img.src = str_src;
            }

            show_result_area.classList.remove("d-none");
            grid_nearest_image.classList.remove("d-none");
            spinner.classList.add("d-none");
        },
    });
}

// drag and drop
$(document).ready(function () {
    const dropContainer = document.getElementById("dropContainer");
    const error = document.getElementById("err");
    // console.log(dropContainer)
    dropContainer.ondragover = function (e) {
        e.preventDefault();
        dropContainer.style.border = "4px dashed green";
        return false;
    };

    dropContainer.ondragleave = function (e) {
        e.preventDefault();
        dropContainer.style.border = "3px dashed #4e7efe";
        return false;
    };

    dropContainer.ondrop = function (e) {
        e.preventDefault();
        dropContainer.style.border = "3px dashed #4e7efe";
        let link = e.dataTransfer.getData("text/html");
        let dropContext = $("<div>").append(link);
        let imgURL = $(dropContext).find("img").attr("src");
        if (imgURL) {
        fetch(imgURL)
            .then((res) => res.blob())
            .then((blob) => {
            error.style.display = "none";
            let index = imgURL.lastIndexOf("/") + 1;
            let filename = imgURL.substr(index);
            let allowedName = /(\.jpg|\.jpeg|\.png|\.gif)$/i;
            if (imgURL.includes("base64")) {
                error.innerText = "⚠️ Không thể kéo ảnh này, hãy mở nó ra rồi kéo";
                error.style.display = "block";
                return;
            }
            if (!allowedName.exec(filename)) {
                error.innerText =
                "⚠️ Không thể upload file này, vui lòng upload file khác";
                error.style.display = "block";
                return;
            }
            if (!filename.includes(".")) {
                error.innerText =
                "⚠️ Không thể upload file này, vui lòng upload file khác";
                error.style.display = "block";
                return;
            }
            process(blob, filename, true);
            })
            .catch(() => {
            error.innerText =
                "⚠️ Không thể upload file này, vui lòng upload file khác";
            error.style.display = "block";
            });
        } else {
        const file = e.dataTransfer.files[0];
        const fileType = file["type"];
        const validImageTypes = ["image/gif", "image/jpeg", "image/png"];
        if (!validImageTypes.includes(fileType)) {
            error.innerText =
            "⚠️ Không thể upload file này, vui lòng upload file khác";
            error.style.display = "block";
        } else {
            error.style.display = "none";
            let blob = new Blob([file], { type: "image/jpeg" });
            let fname = file.name;
            process(blob, fname, true);
        }
        }
    };
});

function relevance_feedback() {
    if (show_result_area.classList.contains("d-none") === false) {
        show_result_area.classList.add("d-none");
    }

    var precision_area = document.getElementById("precision");

    runtime_header.classList.add('d-none');
    runtime_show.innerText = "";

    precision_area.innerHTML = 'waiting for relevance feedback...';
    spinner_rf.classList.remove('d-none');
    
    input_data = {
        "query_path": query_path,
        "query_features": query_features,
        "nearest_images": nearest_images,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "labeled_data_set": labeled_data_set,
        "unlabeled_data_set_indices": unlabeled_data_set_indices
    };
    input_data = JSON.stringify(input_data);

    const data = new FormData();
    data.append("relevance_feedback", input_data);
    $.ajax({
        url: "/",
        type: "POST",
        processData: false,
        contentType: false,
        data: data,
        success: (ret) => {
            var data = ret.data;
            
            n_pos = data['n_pos'];
            n_neg = data['n_neg'];
            labeled_data_set = data['labeled_data_set'];
            unlabeled_data_set_indices = data['unlabeled_data_set_indices'];
           
            var precision = n_pos / 100;
            precision_area.innerText = "" + precision;
            
            runtime = data['run_time'];
            runtime_header.classList.remove('d-none');
            runtime_show.innerText = "" + runtime;

            nearest_images = data['nearest_images'];
            show_nearest_images = data['show_nearest_images'];
            query_path = data['query_path'];
            query_features = data['query_features'];

            var arr_split = query_path.split("__");
            var temp = arr_split[0].split('/');
            var query_class = temp[temp.length-1];
            var query_name = arr_split[1] + '.jpg';
            
            var nearest_img = null;
            var img_class = null;
            var img_name = null;

            for (i = 0 ; i < 100 ; i++) {
                d = show_result_area_children[i];
                children_div = d.children;
                img = d.getElementsByTagName("img")[0];
                rel_or_not = d.getElementsByTagName("p")[0];

                if (rel_or_not.classList.contains("text-success") === true) {
                    rel_or_not.classList.remove("text-success");
                }
                if (rel_or_not.classList.contains("text-danger") === true) {
                    rel_or_not.classList.remove("text-danger");
                }

                nearest_img = show_nearest_images[i];
                img_class = nearest_img.class;
                img_name = nearest_img.name;

                if (img_class === query_class){
                    rel_or_not.classList.add('text-success');
                    rel_or_not.innerText = "RELEVANT";
                }
                else {
                    rel_or_not.classList.add('text-danger');
                    rel_or_not.innerText = "NON-RELEVANT";
                }
                
                var str_src = "static/CorelDB1K/" + img_class + "/"+img_name;
                img.src = str_src;
            }

            show_result_area.classList.remove("d-none");
            grid_nearest_image.classList.remove("d-none");
            spinner_rf.classList.add('d-none');
        },
    });
}


/* ============================================ */
/* Scroll Back To Top Button */
/* ============================================ */
// Get the button:
let mybutton = document.getElementById("myBtn");

// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function() {scrollFunction()};

function scrollFunction() {
    if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
        mybutton.style.display = "block";
    } else {
        mybutton.style.display = "none";
    }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
    document.body.scrollTop = 0; // For Safari
    document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}