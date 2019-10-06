var audio_context;
var recorder;
var audio_stream;

function Initialize() {
  try {
    // Monkeypatch for AudioContext, getUserMedia and URL
    window.AudioContext = window.AudioContext || window.webkitAudioContext;
    navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia;
    window.URL = window.URL || window.webkitURL;

    // Store the instance of AudioContext globally
    audio_context = new AudioContext;
    console.log('Audio context is ready !');
    console.log('navigator.getUserMedia ' + (navigator.getUserMedia ? 'available.' : 'not present!'));
  } catch (e) {
    alert('No web audio support in this browser!');
  }
}


function startRecording() {
  // Access the Microphone using the navigator.getUserMedia method to obtain a stream
  navigator.getUserMedia({ audio: true }, function (stream) {
    // Expose the stream to be accessible globally
    audio_stream = stream;
    // Create the MediaStreamSource for the Recorder library
    var input = audio_context.createMediaStreamSource(stream);
    console.log('Media stream succesfully created');

    // Initialize the Recorder Library
    recorder = new Recorder(input);
    console.log('Recorder initialised');

    // Start recording !
    recorder && recorder.record();
    console.log('Recording...');


    try {
      // Disable Record button and enable stop button !
      document.getElementById("start-btn").disabled = true;
      document.getElementById("stop-btn").disabled = false;
    }
    catch (err) {

    }

  }, function (e) {
    console.error('No live audio input: ' + e);
  });
}

function stopRecording(callback, AudioFormat) {
  // Stop the recorder instance
  recorder && recorder.stop();
  console.log('Stopped recording.');

  // Stop the getUserMedia Audio Stream !
  audio_stream.getAudioTracks()[0].stop();

  // Disable Stop button and enable Record button !
  try {
    // Handle on start recording button
    document.getElementById("start-btn").disabled = false;
    document.getElementById("stop-btn").disabled = true;
  }
  catch (err) {

  }


  // Use the Recorder Library to export the recorder Audio as a .wav file
  // The callback providen in the stop recording method receives the blob
  if (typeof (callback) == "function") {

    /**
     * Export the AudioBLOB using the exportWAV method.
     * Note that this method exports too with mp3 if
     * you provide the second argument of the function
     */
    recorder && recorder.exportWAV(function (blob) {
      callback(blob);
      //recorder && recorder.download(blob, 'my-audio-file');

      // create WAV download link using audio data blob
      //createDownloadLink();

      // Clear the Recorder to start again !
      recorder.clear();
    }, (AudioFormat || "audio/wav"));
  }
}

window.onload = function () {
  // Prepare and check if requirements are filled
  Initialize();
  try {
    // Handle on start recording button
    document.getElementById("start-btn").addEventListener("click", function () {
      startRecording();
    }, false);
  }
  catch (err) {
    document.getElementById("start-btn-v1").addEventListener("click", function () {
      startRecording();
    }, false);
  }

  try {
    // Handle on stop recording button
    document.getElementById("stop-btn").addEventListener("click", function () {
      // Use wav format
      var _AudioFormat = "audio/wav";
      // You can use mp3 to using the correct mimetype
      //var AudioFormat = "audio/mpeg";

      stopRecording(function (AudioBLOB) {
        // Note:
        // Use the AudioBLOB for whatever you need, to download
        // directly in the browser, to upload to the server, you name it !

        // In this case we are going to add an Audio item to the list so you
        // can play every stored Audio
        var url = URL.createObjectURL(AudioBLOB);
        var li = document.createElement('li');
        var au = document.createElement('audio');
        var hf = document.createElement('a');

        au.controls = true;
        au.src = url;
        hf.href = url;
        // Important:
        // Change the format of the file according to the mimetype
        // e.g for audio/wav the extension is .wav 
        //     for audio/mpeg (mp3) the extension is .mp3
        var username = document.getElementById("username").innerHTML;
        var image_title = document.getElementById("title").innerHTML;
        hf.download = username + "_" + image_title + "_" + new Date().toISOString() + '.wav';
        //console.log(hf.download);
        hf.innerHTML = hf.download;
        hf.setAttribute("id", "to_click");
        li.appendChild(au);
        li.appendChild(hf);
        li.click();
        recordingslist.appendChild(li);


        //TODO:
        //Enable to allow auto download to downloads folder
        //document.getElementById('to_click').click();
        //var upload = document.getElementById('to_click');

        /*================ Send Bolb*/

        /*upload.addEventListener("click", function (event) {
          var xhr = new XMLHttpRequest();
          xhr.onload = function (e) {
            if (this.readyState === 4) {
              console.log("Server returned: ", e.target.responseText);
            }
          };
          var fd = new FormData();
    
          var filename = new Date().toISOString();
    
          fd.append("audio_data", AudioBLOB, filename);
          xhr.open("POST", "/uploadfile", true);
          xhr.send(fd);
        })*/
        submit(AudioBLOB);
        /*================ Send Bolb*/
      }, _AudioFormat);
    }, false);
  }
  catch (err) {
    // Handle on stop recording button
    document.getElementById("stop-btn-v1").addEventListener("click", function () {
      // Use wav format
      var _AudioFormat = "audio/wav";
      // You can use mp3 to using the correct mimetype
      //var AudioFormat = "audio/mpeg";

      stopRecording(function (AudioBLOB) {
        // Note:
        // Use the AudioBLOB for whatever you need, to download
        // directly in the browser, to upload to the server, you name it !

        // In this case we are going to add an Audio item to the list so you
        // can play every stored Audio
        var url = URL.createObjectURL(AudioBLOB);
        var li = document.createElement('li');
        var au = document.createElement('audio');
        var hf = document.createElement('a');

        au.controls = true;
        au.src = url;
        hf.href = url;
        // Important:
        // Change the format of the file according to the mimetype
        // e.g for audio/wav the extension is .wav 
        //     for audio/mpeg (mp3) the extension is .mp3
        var username = document.getElementById("username").innerHTML;
        var image_title = document.getElementById("title").innerHTML;
        hf.download = username + "_" + image_title + "_" + new Date().toISOString() + '.wav';
        //console.log(hf.download);
        hf.innerHTML = hf.download;
        hf.setAttribute("id", "to_click");
        li.appendChild(au);
        li.appendChild(hf);
        li.click();
        recordingslist.appendChild(li);


        //TODO:
        //Enable to allow auto download to downloads folder
        //document.getElementById('to_click').click();
        //var upload = document.getElementById('to_click');

        /*================ Send Bolb*/

        /*upload.addEventListener("click", function (event) {
          var xhr = new XMLHttpRequest();
          xhr.onload = function (e) {
            if (this.readyState === 4) {
              console.log("Server returned: ", e.target.responseText);
            }
          };
          var fd = new FormData();
    
          var filename = new Date().toISOString();
    
          fd.append("audio_data", AudioBLOB, filename);
          xhr.open("POST", "/uploadfile", true);
          xhr.send(fd);
        })*/
        submit(AudioBLOB);
        startRecording();
        /*================ Send Bolb*/
      }, _AudioFormat);
    }, false);
  }





};

function submit(blob) {
  /*
  Sends blob to flask 
  */
  var reader = new window.FileReader();
  reader.readAsDataURL(blob);

  reader.onloadend = function () {
    /*TODO : Add a test to see if username is here*/
    var fd = new FormData();
    var username = document.getElementById("username").innerHTML;
    var image_title = document.getElementById("title").innerHTML;
    var filename = username + "_" + image_title + "_" + new Date().toISOString() + '.wav';
    fd.append('file', blob, filename);

    $.ajax({
      type: 'POST',
      url: '/uploadfile',
      data: fd,
      cache: false,
      processData: false,
      contentType: false,
      enctype: false
    }).done(function (data) {
      console.log("Done");
    });
  }

}
