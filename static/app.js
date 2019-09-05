function init() {
    //Trend Chart Items:
    var SelectedItem = d3.select("#selectItem");
    d3.json("overall_items", function(items) {
        items.forEach((item) => {
            SelectedItem.append("option")
                        .text(item)
                        .property("value",item)
        })
        const FirstItem = items[0];
        buildtrend(FirstItem);
    })

    //Week:
    var SelectedWeek = d3.select("#selectWeek");
    d3.json("/week_list", function(weeks) {
        weeks.forEach(function(week) {
            SelectedWeek.append("option")
                        .text(week)
                        .property("value",week)
        })
        const FirstWeek = weeks[0];
        buildFTpie(FirstWeek);
    })
   
    //Top10 List:
    var SelectTop10 = d3.select("#selectTop10");
    d3.json("/top10_list", function(tops) {
        tops.forEach((top) => {
            SelectTop10.append("option")
                       .text(top)
                       .property("value",top)
        })
        const FirstTop10 = tops[0];
        console.log(FirstTop10);
        buildlist(FirstTop10);
    })
}

function buildtrend(result) {
    d3.json(`/overall_trend/${result}`, function(detail) {
        console.log(detail);
        var TotalWeek = detail.week;
        var ItemWanted = detail[result];
        var TotalDie = detail.total_die;
        console.log(TotalWeek);
        var trace = {
            x: TotalWeek,
            y: ItemWanted,
            marker: {color: 'green'},
            text: TotalDie,
            type: 'scatter'
        };
        var data = [trace];
        var layout ={
            xaxis: { title: "FT Week"},
            yaxis: { title: "Percentage"},
            margin: { b: -6},
            height: 380,
            width: 630
        };
        Plotly.newPlot("trend-plot", data, layout);
    });
}

function buildFTpie(week) {
    d3.json(`/FT_pie/${week}`, function(selectweek) {
        var TotalItems = selectweek.item;
        var FailDetail = selectweek.fail;
        var pieData = [
            {
                values: FailDetail,
                labels: TotalItems,
                type: 'pie'
            }
        ];

        var layout = {
            showlegend: false,
            margin: { t: 0, l: -5 },
            height: 200,
            width: 370,
        };
        Plotly.newPlot('pie', pieData, layout);
        
        d3.select("#CatType").selectAll("li").on("click", function() {
            var SelectItemText = d3.select(this).text();

            if (SelectItemText == "FT") {
                var pieData = [
                    {
                        values: FailDetail.slice(0,5),
                        labels: TotalItems.slice(0,5),
                        type: 'pie'
                    }
                ];

                var layout = {
                    showlegend: false,
                    margin: { t: 0, l: -5 },
                    height: 200,
                    width: 370,
                };
                Plotly.newPlot('pie', pieData, layout);
            }
            else {
                var pieData = [
                    {
                        values: FailDetail.slice(5,10),
                        labels: TotalItems.slice(5,10),
                        type: 'pie'
                    }
                ];

                var layout = {
                    showlegend: false,
                    margin: { t: 0, l: -5 },
                    height: 200,
                    width: 370,
                };
                Plotly.newPlot('pie', pieData, layout);
            }
        });            
    });
}

function buildlist(hbin) {
    d3.json(`/SLLY_list/${hbin}`, function(items) {
        var item = [];
        Object.entries(items).forEach(([key,value]) => {
            item.push(value);
        });
        console.log(item);
        if (item[0] != "No LY lots over the past 9 weeks.") {
            item.forEach(function(lot) {
                var TotalList = d3.select(".summary").selectAll("li").data(lot);
                TotalList.enter().append("li").merge(TotalList).html(d => d);
                TotalList.exit().remove();
            });
        }
        else {
            var NoLYList = d3.select(".summary").selectAll("li").data(item);
            NoLYList.enter().append("li").merge(NoLYList).html(d => d);
            NoLYList.exit().remove();                                          
        }
    });
}

function ItemSelection(newItem) {
    buildtrend(newItem);
}

function WeekSelection(newWeek) {
    buildFTpie(newWeek);
}

function LYSelection(newhbin) {
    buildlist(newhbin);
}

init();   