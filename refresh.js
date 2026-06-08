(function() {
    var btn = document.getElementById("refreshBtn");
    var toast = document.getElementById("toast");
    var tt = null;
    function st(msg, type) {
        toast.textContent = msg;
        toast.className = "toast " + (type || "") + " show";
        if (tt) clearTimeout(tt);
        tt = setTimeout(function() { toast.className = "toast"; }, 2500);
    }
    function fn(n, d) { d = d || 2; return (typeof n === "number") ? n.toFixed(d) : String(n); }
    function fc(v, pct) {
        var n = parseFloat(v);
        if (isNaN(n)) return String(v);
        var s = n > 0 ? "+" : "";
        return s + (pct !== false ? n.toFixed(2) + "%" : n.toFixed(2));
    }
    function cc(v) { var n = parseFloat(v); return isNaN(n) ? "" : n > 0 ? "up" : n < 0 ? "down" : ""; }

    async function fetchAIndices() {
        var codes = {"sh000001":"SH","sz399001":"SZ","sz399006":"CYB","sh000688":"KC50","sh000300":"HS300"};
        var r = await fetch("https://hq.sinajs.cn/list=" + Object.keys(codes).join(","), {headers:{"Referer":"https://finance.sina.com.cn/"}});
        var t = await r.text(), res = [];
        for (var c in codes) {
            var re = new RegExp('var hq_str_' + c + '="([^"]+)"');
            var m = t.match(re);
            if (!m) continue;
            var p = m[1].split(",");
            if (p.length < 6) continue;
            var pr = parseFloat(p[1]) || 0, pv = parseFloat(p[2]) || 0;
            res.push({name:p[0], price:pr, change:pr-pv, changePct:pv?(pr-pv)/pv*100:0, high:parseFloat(p[4])||0, low:parseFloat(p[5])||0});
        }
        return res;
    }
    async function fetchUSIndices() {
        var codes = {"gb_dji":"DJI","gb_ixic":"IXIC","gb_inx":"SPX"};
        var r = await fetch("https://hq.sinajs.cn/list=" + Object.keys(codes).join(","), {headers:{"Referer":"https://finance.sina.com.cn/"}});
        var t = await r.text(), res = [];
        for (var c in codes) {
            var re = new RegExp('var hq_str_' + c + '="([^"]+)"');
            var m = t.match(re);
            if (!m) continue;
            var p = m[1].split(",");
            if (p.length < 5) continue;
            res.push({name:p[0], price:parseFloat(p[1])||0, change:parseFloat(p[4])||0, changePct:parseFloat(p[2])||0});
        }
        return res;
    }
    async function fetchMovers(asc, cnt) {
        var r = await fetch("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num="+(cnt+5)+"&sort=changepercent&asc="+(asc?"1":"0")+"&node=hs_a");
        var d = await r.json(), res = [];
        for (var i = 0; i < d.length && res.length < cnt; i++) {
            var pct = parseFloat(d[i].changepercent) || 0;
            if (!asc && pct <= 0) continue;
            if (asc && pct >= 0) continue;
            res.push({code:d[i].symbol, name:d[i].name, price:d[i].trade||d[i].price, changePct:pct});
        }
        return res;
    }
    async function fetchFinanceNews() {
        var r = await fetch("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=8&page=1&_="+Date.now(), {headers:{"Referer":"https://finance.sina.com.cn/"}});
        var d = await r.json(), items = [];
        var ls = d.result && d.result.data ? d.result.data : [];
        for (var i = 0; i < ls.length && i < 8; i++) {
            var t = (ls[i].title || "").trim();
            if (t) items.push({title:t, url:ls[i].url||"", source:"Sina"});
        }
        return items;
    }
    async function fetchTechNews() {
        var r = await fetch("https://api.ithome.com/json/newslist/news?page=1");
        var d = await r.json(), items = [];
        var adw = ["清仓","元官方","到手","仅售","秒杀","立减","大促","神价"];
        var ls = d.newslist || [];
        for (var i = 0; i < ls.length && items.length < 6; i++) {
            var t = ls[i].title || "";
            if (adw.some(function(w){ return t.indexOf(w)>=0; })) continue;
            var au = ls[i].url || "";
            if (au.indexOf("lapin") >= 0) continue;
            var url = "", nid = String(ls[i].newsid||"");
            if (au && au.charAt(0) === "/") url = "https://www.ithome.com" + au;
            else if (nid.length >= 6) url = "https://www.ithome.com/0/" + nid.substring(0,3) + "/" + nid.substring(3) + ".htm";
            if (t) items.push({title:t, url:url, source:"ITHome"});
        }
        return items;
    }
    function updateAIndices(d) {
        var g = document.querySelector(".section:nth-of-type(1) .stats-grid");
        if (!g || !d.length) return;
        var h = "";
        for (var i = 0; i < d.length; i++) {
            var x = d[i], cl = cc(x.changePct);
            h += '<div class="stat-card"><div class="label">'+x.name+'</div><div class="value">'+fn(x.price)+'</div><div class="change '+cl+'">'+fc(x.changePct)+'</div>';
            if (x.high) h += '<div class="sub">H '+fn(x.high)+' / L '+fn(x.low)+'</div>';
            h += '</div>';
        }
        g.innerHTML = h;
    }
    function updateUSIndices(d) {
        var g = document.querySelector(".section:nth-of-type(2) .stats-grid");
        if (!g || !d.length) return;
        var h = "";
        for (var i = 0; i < d.length; i++) {
            var x = d[i], cl = cc(x.changePct);
            h += '<div class="stat-card"><div class="label">'+x.name+'</div><div class="value">'+fn(x.price)+'</div><div class="change '+cl+'">'+fc(x.change,false)+' ('+fc(x.changePct)+')</div></div>';
        }
        g.innerHTML = h;
    }
    function updateMovers(ga, lo) {
        var tbs = document.querySelectorAll(".section:nth-of-type(3) table");
        if (ga && ga.length && tbs.length >= 1) {
            var h = "";
            for (var i = 0; i < ga.length; i++) {
                var s = ga[i];
                h += '<tr><td>'+s.code+'</td><td>'+s.name+'</td><td>'+fn(s.price)+'</td><td class="up">'+fc(s.changePct)+'</td></tr>';
            }
            tbs[0].querySelector("tbody").innerHTML = h;
        }
        if (lo && lo.length && tbs.length >= 2) {
            var h = "";
            for (var i = 0; i < lo.length; i++) {
                var s = lo[i];
                h += '<tr><td>'+s.code+'</td><td>'+s.name+'</td><td>'+fn(s.price)+'</td><td class="down">'+fc(s.changePct)+'</td></tr>';
            }
            tbs[1].querySelector("tbody").innerHTML = h;
        }
    }
    function updateNews(fin, tec) {
        var ls = document.querySelectorAll(".news-list");
        if (fin && fin.length && ls.length >= 1) {
            var h = "";
            for (var i = 0; i < fin.length; i++) {
                var it = fin[i];
                var ti = it.url ? '<a href="'+it.url+'" target="_blank" rel="noopener">'+it.title+'</a>' : it.title;
                h += '<li><span class="tag tag-sina">'+it.source+'</span>'+ti+'</li>';
            }
            ls[0].innerHTML = h;
        }
        if (tec && tec.length && ls.length >= 2) {
            var h = "";
            for (var i = 0; i < tec.length; i++) {
                var it = tec[i];
                var ti = it.url ? '<a href="'+it.url+'" target="_blank" rel="noopener">'+it.title+'</a>' : it.title;
                h += '<li><span class="tag tag-ithome">'+it.source+'</span>'+ti+'</li>';
            }
            ls[1].innerHTML = h;
        }
    }
    function updateNewStocks() {
        fetch("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=10&sort=changepercent&asc=0&node=new_stock")
            .then(function(r) { return r.json(); })
            .then(function(d) {
                var tb = document.querySelector(".section:nth-of-type(4) table tbody");
                if (!tb || !d.length) return;
                var h = "";
                for (var i = 0; i < Math.min(6, d.length); i++) {
                    var s = d[i], cl = cc(s.changepercent);
                    h += '<tr><td>'+s.symbol+'</td><td>'+s.name+'</td><td>'+fn(s.trade)+'</td><td class="'+cl+'">'+fc(s.changepercent)+'</td><td>'+fn(s.open)+'</td></tr>';
                }
                tb.innerHTML = h;
            });
    }
    function updateTime() {
        var now = new Date();
        var el = document.querySelector(".header .time");
        if (el) el.textContent = "Refreshed " + now.toTimeString().substring(0,8) + " HKT";
    }

    btn.addEventListener("click", async function() {
        btn.classList.add("spinning");
        btn.classList.remove("success", "error");
        var ok = 0, total = 5;
        try { var a = await fetchAIndices(); updateAIndices(a); ok++; } catch(e) { console.log(e); }
        try { var u = await fetchUSIndices(); updateUSIndices(u); ok++; } catch(e) { console.log(e); }
        try { var g = await fetchMovers(false,5); var l = await fetchMovers(true,5); updateMovers(g,l); ok++; } catch(e) { console.log(e); }
        try { var fn = await fetchFinanceNews(); var tn = await fetchTechNews(); updateNews(fn,tn); ok++; } catch(e) { console.log(e); }
        try { updateNewStocks(); ok++; } catch(e) { console.log(e); }
        updateTime();
        btn.classList.remove("spinning");
        if (ok >= 4) { btn.classList.add("success"); st("Refreshed ("+ok+"/"+total+")", "ok"); }
        else if (ok >= 2) { st("Partial ("+ok+"/"+total+")", "ok"); }
        else { btn.classList.add("error"); st("Network error, retry", "err"); }
        setTimeout(function() { btn.classList.remove("success","error"); }, 3000);
    });
})();