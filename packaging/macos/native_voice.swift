// Original IGRIS native adapter. OS voices only; no download, cloning or listener.
import Foundation
import AVFoundation
import Speech

enum VoiceError: Error { case unavailable, denied, invalid, timeout }
let locales = ["en":"en-IN", "hi":"hi-IN", "mr":"mr-IN"]
func waitFor(_ complete: () -> Bool, seconds: Double) throws {
    let deadline = Date().addingTimeInterval(seconds)
    while !complete() {
        if Date() > deadline { throw VoiceError.timeout }
        RunLoop.current.run(until: Date().addingTimeInterval(0.02))
    }
}
func json(_ value: [String:Any]) throws {
    let bytes = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    FileHandle.standardOutput.write(bytes); FileHandle.standardOutput.write(Data([10]))
}
func fileURL(_ value: Any?) throws -> URL {
    guard let path = value as? String, path.hasPrefix("/"), !path.contains("\0") else { throw VoiceError.invalid }
    return URL(fileURLWithPath: path)
}
func recognize(_ url: URL, _ locale: String) throws -> String {
    var status = SFSpeechRecognizer.authorizationStatus()
    if status == .notDetermined {
        var done = false
        SFSpeechRecognizer.requestAuthorization { value in status = value; done = true }
        try waitFor({done}, seconds: 20)
    }
    guard status == .authorized else { throw VoiceError.denied }
    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale)), recognizer.isAvailable,
          recognizer.supportsOnDeviceRecognition else { throw VoiceError.unavailable }
    let request = SFSpeechURLRecognitionRequest(url: url)
    request.requiresOnDeviceRecognition = true
    request.shouldReportPartialResults = false
    var done = false; var text: String?; var failed = false
    let task = recognizer.recognitionTask(with: request) { result, error in
        if let result = result, result.isFinal { text = result.bestTranscription.formattedString; done = true }
        if error != nil { failed = true; done = true }
    }
    defer { task.cancel() }
    try waitFor({done}, seconds: 45)
    guard !failed, let value = text, !value.isEmpty else { throw VoiceError.unavailable }
    return value
}
func record(_ url: URL, _ seconds: Double) throws {
    guard seconds >= 1 && seconds <= 30 else { throw VoiceError.invalid }
    var allowed = AVCaptureDevice.authorizationStatus(for: .audio) == .authorized
    if AVCaptureDevice.authorizationStatus(for: .audio) == .notDetermined {
        var done = false
        AVCaptureDevice.requestAccess(for: .audio) { value in allowed = value; done = true }
        try waitFor({done}, seconds: 20)
    }
    guard allowed else { throw VoiceError.denied }
    let engine = AVAudioEngine(); let input = engine.inputNode
    let source = input.outputFormat(forBus: 0)
    guard source.sampleRate > 0, source.channelCount > 0,
          let target = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true),
          let converter = AVAudioConverter(from: source, to: target) else { throw VoiceError.unavailable }
    let output = try AVAudioFile(forWriting: url, settings: target.settings, commonFormat: .pcmFormatInt16, interleaved: true)
    var frames: AVAudioFrameCount = 0; var failed = false
    let lock = NSLock()
    input.installTap(onBus: 0, bufferSize: 2048, format: source) { buffer, _ in
        lock.lock(); defer { lock.unlock() }
        if failed || frames >= 480000 { return }
        guard let converted = AVAudioPCMBuffer(pcmFormat: target, frameCapacity: 8192) else { failed = true; return }
        var supplied = false; var conversionError: NSError?
        let status = converter.convert(to: converted, error: &conversionError) { _, state in
            if supplied { state.pointee = .noDataNow; return nil }
            supplied = true; state.pointee = .haveData; return buffer
        }
        if status == .error || conversionError != nil { failed = true; return }
        converted.frameLength = min(converted.frameLength, 480000 - frames)
        do { try output.write(from: converted); frames += converted.frameLength } catch { failed = true }
    }
    defer { engine.stop(); input.removeTap(onBus: 0) }
    try engine.start()
    RunLoop.current.run(until: Date().addingTimeInterval(seconds))
    engine.stop(); lock.lock(); let valid = !failed && frames > 0; lock.unlock()
    guard valid else { throw VoiceError.unavailable }
}
func synthesize(_ text: String, _ locale: String, _ url: URL) throws -> String {
    guard !text.isEmpty, text.count <= 240 else { throw VoiceError.invalid }
    let language = String(locale.prefix(2))
    guard let voice = AVSpeechSynthesisVoice.speechVoices().first(where: {$0.language == locale}) ??
        AVSpeechSynthesisVoice.speechVoices().first(where: {$0.language.hasPrefix(language + "-")}) else { throw VoiceError.unavailable }
    let utterance = AVSpeechUtterance(string: text); utterance.voice = voice
    utterance.rate = 0.42; utterance.pitchMultiplier = 0.85
    let synthesizer = AVSpeechSynthesizer(); var file: AVAudioFile?; var done = false; var failed = false
    synthesizer.write(utterance) { buffer in
        guard let audio = buffer as? AVAudioPCMBuffer else { failed = true; done = true; return }
        if audio.frameLength == 0 { done = true; return }
        do {
            if file == nil { file = try AVAudioFile(forWriting: url, settings: audio.format.settings) }
            try file?.write(from: audio)
        } catch { failed = true; done = true }
    }
    defer { synthesizer.stopSpeaking(at: .immediate) }
    try waitFor({done}, seconds: 30)
    guard !failed, file != nil else { throw VoiceError.unavailable }
    return voice.identifier
}
do {
    let raw = FileHandle.standardInput.readDataToEndOfFile()
    guard raw.count <= 16384, let request = try JSONSerialization.jsonObject(with: raw) as? [String:Any],
          let operation = request["operation"] as? String else { throw VoiceError.invalid }
    if operation == "capabilities" {
        var rows = [[String:Any]]()
        for (language, locale) in locales.sorted(by: {$0.key < $1.key}) {
            let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale))
            rows.append(["language":language,"locale":locale,"on_device_recognition":recognizer?.supportsOnDeviceRecognition ?? false,
                         "voices":AVSpeechSynthesisVoice.speechVoices().filter {$0.language.hasPrefix(language + "-")}.map {$0.identifier}])
        }
        try json(["status":"capabilities_only","languages":rows,"microphone_started":false,"human_acceptance":false])
    } else {
        guard let language = request["language"] as? String, let locale = locales[language] else { throw VoiceError.invalid }
        let path = try fileURL(request["path"])
        switch operation {
        case "record":
            guard let seconds = request["seconds"] as? Double else { throw VoiceError.invalid }
            try record(path, seconds); try json(["status":"recorded","language":language])
        case "transcribe":
            let text = try recognize(path, locale)
            try json(["status":"transcribed","text":text,"language":language,"language_selection":"explicit","on_device_required":true])
        case "synthesize":
            guard let text = request["text"] as? String else { throw VoiceError.invalid }
            let voice = try synthesize(text, locale, path)
            try json(["status":"generated_file_only","voice":voice,"language":language,"speaker_playback_verified":false])
        default: throw VoiceError.invalid
        }
    }
} catch {
    // No audio, transcript, private paths or OS diagnostic text in errors.
    try? json(["status":"unavailable","error":String(describing: error is VoiceError ? error : VoiceError.unavailable),"text_fallback":true])
    exit(2)
}
