function validateForm() {
    let password0 = document.getElementById("password0").value;
    let password1 = document.getElementById("password1").value;
    if (password0 != password1) {
        $('.passwords-match').popover('show');
        $('.popover-body').click(function () {
            $('.passwords-match').popover("hide");
        });
        document.body.scrollTop = 0;
        document.documentElement.scrollTop = 0;
        $("#password0").css("outline", "1px solid red");
        $("#password1").css("outline", "1px solid red");
        return false;
    } else {
        return password1;
    }
}

$(document).on("submit", ".bootbox form", function (e) {
    e.preventDefault();
    $(".bootbox .btn-primary").click();
});

$(".edit_password").on("click", async function () {
    const token = getCookie("_xsrf");
    let user_id = $(this).data('id');
    bootbox.dialog({
        message: `
    <form class="form" id='infos' action=''>
      <div class="form-group">
        <label for="new_password">${$(this).data("translate1")}</label>
        <input class="form-control" type='password' id="password0" name='new_password' /><br>
      </div>
      <div class="form-group">
        <label for="confirm_password">${$(this).data("translate2")}</label>
        <input class="form-control" type='password' id="password1" name='confirm_password' />
      </div>
    </form>
  `,
        buttons: {
            cancel: {
                label: "Cancel",
                className: "btn-secondary"
            },
            confirm: {
                label: "OK",
                className: "btn-primary",
                callback: function () {
                    let password = validateForm();
                    if (!password) {
                        return false;
                    }

                    (async () => {
                        password = password.toString();
                        let res = await fetch(`/api/v2/users/${user_id}`, {
                            method: 'PATCH',
                            headers: { 'X-XSRFToken': token },
                            body: JSON.stringify({ "password": password }),
                        });
                        let responseData = await res.json();

                        if (responseData.status === "ok") {
                            console.log(responseData.data);
                            bootbox.hideAll();
                        } else {
                            bootbox.hideAll();
                            bootbox.alert({
                                title: responseData.status,
                                message: responseData.error_data
                            });
                        }
                    })();
                }
            }
        }
    });

});

$(".edit_user").on("click", function () {
    const token = getCookie("_xsrf");
    let username = $(this).data('name');
    let user_id = $(this).data('id');
    bootbox.confirm(`<form class="form" id='infos' action=''>\
      <div class="form-group">
      <label for="username">${$(this).data("translate")}</label>
      <input class="form-control" type='text' name='username' id="username_field" value=${username} /><br/>\
      </div>
      </form>`, async function (result) {
        if (result) {
            let new_username = $("#username_field").val();
            let res = await fetch(`/api/v2/users/${user_id}`, {
                method: 'PATCH',
                headers: {
                    'X-XSRFToken': token
                },
                body: JSON.stringify({ "username": new_username }),
            });
            let responseData = await res.json();
            if (responseData.status === "ok") {
                $(`#user_${user_id}`).html(` ${new_username}`)
                $(`#username_${user_id}`).data('name', new_username);
            } else {

                bootbox.alert({
                    title: responseData.error,
                    message: responseData.error_data
                });
            }
        }
    }
    )
});