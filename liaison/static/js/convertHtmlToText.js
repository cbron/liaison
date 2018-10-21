function convertHtmlToText(html) {
    var inputText = html;
    var returnText = "" + inputText;
    console.log('1');
    console.log(returnText);
    //-- remove BR tags and replace them with line break
    returnText=returnText.replace(/<br>/gi, "\n");
    returnText=returnText.replace(/<br\s\/>/gi, "\n");
    returnText=returnText.replace(/<br\/>/gi, "\n");
    console.log('2');
    console.log(returnText);
    //-- remove P and A tags but preserve what's inside of them
    returnText=returnText.replace(/<p.*?>/gi, "\n");
    console.log('2.5');
    console.log(returnText);
    returnText=returnText.replace(/<a.*href="(.*?)".*>(.*?)<\/a>/gi, " $2 ($1)");
    console.log('3');
    console.log(returnText);
    //-- remove all inside SCRIPT and STYLE tags
    returnText=returnText.replace(/<script.*>[\w\W]{1,}(.*?)[\w\W]{1,}<\/script>/gi, "");
    returnText=returnText.replace(/<style.*>[\w\W]{1,}(.*?)[\w\W]{1,}<\/style>/gi, "");
    //-- remove all else
    returnText=returnText.replace(/<(?:.|\s)*?>/g, "");
    console.log('4');
    console.log(returnText);
    //-- get rid of more than 2 multiple line breaks:
    returnText=returnText.replace(/(?:(?:\r\n|\r|\n)\s*){2,}/gim, "\n\n");
    console.log('5');
    console.log(returnText);
    //-- get rid of more than 2 spaces:
    returnText = returnText.replace(/ +(?= )/g,'');
    console.log('6');
    console.log(returnText);
    //-- get rid of html-encoded characters:
    returnText=returnText.replace(/&nbsp;/gi," ");
    returnText=returnText.replace(/&amp;/gi,"&");
    returnText=returnText.replace(/&quot;/gi,'"');
    returnText=returnText.replace(/&lt;/gi,'<');
    returnText=returnText.replace(/&gt;/gi,'>');

    //-- return
    return returnText;
}