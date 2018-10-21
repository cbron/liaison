$(document).ready(function() {

    var buttons = ['bold', 'italic', 'underline', 'strikeThrough', 'subscript', 'superscript', 'fontFamily', 'fontSize', 'color', 'formatBlock', 'blockStyle', 'align', 'insertOrderedList', 'insertUnorderedList', 'outdent', 'indent', 'createLink', 'insertImage', 'table', 'undo', 'redo', 'html', 'fullscreen'];
    $("#email-editor")
        .editable({
            inlineMode: false,
            fullPage: true,
            minHeight: 300,
            allowStyle: true,
            beautifyCode: false,
            buttons: buttons
        })
        .on('editable.imageError', function (e, editor, error) {
            $(".editor-error").slideDown().delay(5000).slideUp();
      });


    $("#footer-editor")
        .editable({
            inlineMode: false,
            theme: 'dark',
            minHeight: 300
    });

    // Two chosen boxes in dispatcher
    $("#dispatcher_lists").find('select').chosen({no_results_text: "Oops, nothing found!", width: "45%"});

    // Setup chosen list select on campaign page
    $(".campaign_list_select").chosen({ allow_single_deselect:true, width: "250px" });

    // Chosen preselected on page load, and select fields filled from list keys
    list_id = $("#list_identifier").val()
    if(list_id){
        $('.campaign_list_select').val(list_id);
        $('.campaign_list_select').trigger('chosen:updated');
        campaign_list_select_filler(list_id, false)
    }


    $(".dd-key").css( 'cursor', 'pointer' );
    $(".dd-key").click(function() {
        $("#email-editor").editable("insertHTML", "{{ " + $(this).html() + " }}", true);
    });

    $(".show-html").click(function() {
        $(".text-from-html").fadeOut(function(){$(".html-to-text").fadeIn(); });
        return false;
    });

    $(".show-text").click(function() {
        $(".html-to-text").fadeOut(function(){$(".text-from-html").fadeIn(); });
        return false;
    });

    $(".template-style").click(function() {
        $("#template").val($(this).children('span').data('template-id'));
        $(".template-style").children('.template-title').removeClass('template-style-selected');
        $(this).children('.template-title').addClass('template-style-selected');
        return false;
    });

    $("#auto-text-checkbox").click(function() {
        auto_text = 0
        if($("#auto-text-checkbox").is(':checked')){
            auto_text = 1
        };
        $.ajax( {
            type: 'POST',
            url: '/accounts/auto_text',
            data: { 'auto_text' : auto_text}
        });
    });

    // On chosen list select change, update select boxes and update object
    // campaigns/{id}/edit
    $(".campaign_list_select").change(function() {
        $("#list_updated").fadeOut('fast');
        if (this.value){
            update_campaign_list(this.value);
            campaign_list_select_filler(this.value, true);
        };
    });

    // Multi-select on campaigns/{id}/emails/{id}/edit
    if( $("#selector_col_val").length > 0 ){
        $("#selector_col_val").chosen({
            multiple: true,
            width: "300px;"
        });
    }

    if( $("#guide").length > 0 ){
        $('body').scrollspy({
            target: '.bs-docs-sidebar',
            offset: 200
        });

        var offset = 60;
        $('.bs-docs-sidebar li a').click(function(event) {
            event.preventDefault();
            $($(this).attr('href'))[0].scrollIntoView();
            scrollBy(0, -offset);
        });
    }

});


function update_campaign_list(list_id){
    campaign_id = $("#campaign_identifier").val()
    $.ajax({
        url : '/campaigns/' + campaign_id + '/list_update',
        type : 'POST',
        data : {
            'list_id' : list_id
        },
        success : function(data) {
            $("#list_updated").fadeIn('fast');
        },
        dataType:'json'
    });
};

function campaign_list_select_filler(list_id, select_fields){
    $.ajax({
        url : '/campaigns/list_select',
        type : 'GET',
        data : {
            'list_id' : list_id
        },
        dataType:'json',
        success : function(data) {
            str = "<ul>"; // sidebar
            options = '<option value></option>'; // select fields
            data.forEach(function(item) {
                str += "<li>" + item + "</li>";
                options += '<option value="' + item + '">' + item + '</option>';
            });
            str += "</ul>"
            $('#campaign_list_select_result').html(str).show();
            if (select_fields){
                $('.dd-options').html(options);
            }
            $('.dd-options').css({'color': 'black'});
        }
    });

    $("#list_id").val(list_id);
};
